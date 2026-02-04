"""
Pipeline Factory - Creates pipelines from configuration.
Makes the system fully modular and config-driven.
"""
import logging
from typing import List, Dict, Any

from core.entities import DigestEntry
from ingestion.source_factory import create_adapters_from_config
from processing.prefilter import passes_prefilter, filter_duplicates
from processing.summarizer import summarize_cluster
from processing.evaluator import evaluate_batch
from services.llm import OllamaClient
from services.config import PipelineConfig
from services.digest_tracker import DigestTracker
from workflows.base import PersonaPipeline

logger = logging.getLogger(__name__)


class ConfigurablePipeline(PersonaPipeline):
    """
    A generic, config-driven pipeline that works for any persona.
    All behavior is determined by the PipelineConfig passed in.
    """

    def __init__(
        self,
        pipeline_config: PipelineConfig,
        llm: OllamaClient,
        tracker: DigestTracker,
    ):
        self.pipeline_config = pipeline_config
        self.persona = pipeline_config.persona
        self.llm = llm
        self.tracker = tracker

        # Ingestion settings
        self.sources = create_adapters_from_config(pipeline_config.ingestion)
        self.keywords = pipeline_config.ingestion.keywords
        self.min_engagement = pipeline_config.ingestion.min_engagement
        self.top_k = pipeline_config.ingestion.top_k
        self.fetch_hours = pipeline_config.fetch_hours

        # Result formatting
        self.default_audience = pipeline_config.default_audience
        self.score_field = pipeline_config.score_field
        self.why_it_matters_field = pipeline_config.why_it_matters_field
        self.why_it_matters_fallback = pipeline_config.why_it_matters_fallback

    @property
    def name(self) -> str:
        return self.persona.name

    async def run(self) -> List[DigestEntry]:
        digest_entries: List[DigestEntry] = []

        try:
            # Fetch all items from sources
            items = []
            for source in self.sources:
                try:
                    fetched = await source.fetch_items(hours=self.fetch_hours)
                    items.extend(fetched)
                except Exception as e:
                    logger.error(f"Source {source.__class__.__name__} failed: {e}")

            logger.info(f"[{self.name}] Fetched {len(items)} items from sources")

            if not items:
                logger.info(f"[{self.name}] No items fetched")
                return []

            # Pre-filter items by keywords and engagement
            filtered_items = [
                item for item in items
                if passes_prefilter(
                    item,
                    keywords=self.keywords,
                    min_engagement=self.min_engagement,
                )
            ]

            logger.info(f"[{self.name}] After keyword filter: {len(filtered_items)} items")

            if not filtered_items:
                logger.info(f"[{self.name}] No items passed pre-filter")
                return []

            # Deduplication: Remove items already sent
            unique_items = await filter_duplicates(filtered_items, self.tracker)

            if not unique_items:
                logger.info(f"[{self.name}] No unique items after deduplication")
                return []

            logger.info(f"[{self.name}] After deduplication: {len(unique_items)} unique items")

            # Prepare batch for single LLM call
            batch_items = [
                {
                    "id": str(i),
                    "title": item.title,
                    "content": item.content,
                    "url": item.url,
                }
                for i, item in enumerate(unique_items)
            ]

            logger.info(f"[{self.name}] Sending {len(batch_items)} items for evaluation (selecting top {self.top_k})")

            # Single LLM call for all items - returns top_k
            try:
                evaluations = await evaluate_batch(
                    llm=self.llm,
                    persona=self.persona,
                    items=batch_items,
                    top_k=self.top_k,
                )
            except Exception as eval_error:
                logger.error(f"[{self.name}] Batch evaluation failed: {eval_error}")
                return []

            # Process results - only the selected top items
            for eval_result in evaluations:
                item_id = eval_result["id"]
                try:
                    item_idx = int(item_id)
                    item = unique_items[item_idx]
                except (ValueError, IndexError):
                    logger.warning(f"[{self.name}] Invalid item ID from LLM: {item_id}")
                    continue

                parsed = eval_result.get("parsed")
                if not parsed:
                    continue

                # Extract score using configured field
                score = parsed.get(self.score_field, 0.0)

                # Build why_it_matters from configured field(s)
                why_it_matters = self._build_why_it_matters(parsed)

                # Get audience from parsed or use default
                audience = parsed.get("target_audience", self.default_audience)

                entry = summarize_cluster(
                    persona=self.persona,
                    title=item.title,
                    summary=item.content[:400],
                    why_it_matters=why_it_matters,
                    audience=audience,
                    source_urls=[item.url],
                    structured_output=parsed,
                )

                digest_entries.append(entry)

                # Record sent digest for future deduplication
                await self.tracker.record_sent_digest(
                    url=item.url,
                    title=item.title,
                    persona=self.name,
                    relevance_score=score,
                    content=item.content,
                )

                logger.info(f"[{self.name}] Included item: {item.title} (score: {score})")

        except Exception as e:
            logger.exception(f"[{self.name}] Pipeline error: {e}")
            return []

        return digest_entries[:self.top_k]

    def _build_why_it_matters(self, parsed: Dict[str, Any]) -> str:
        """Build the why_it_matters string from parsed evaluation."""
        if isinstance(self.why_it_matters_field, str):
            # Single field
            return parsed.get(self.why_it_matters_field, self.why_it_matters_fallback)
        elif isinstance(self.why_it_matters_field, list):
            # Multiple fields to concatenate
            parts = [parsed.get(field, "") for field in self.why_it_matters_field]
            result = " ".join(p.strip() for p in parts if p).strip()
            return result if result else self.why_it_matters_fallback
        else:
            return self.why_it_matters_fallback


def create_pipelines_from_config(
    pipelines_config: List[PipelineConfig],
    llm: OllamaClient,
    tracker: DigestTracker,
) -> List[PersonaPipeline]:
    """
    Factory function to create pipeline instances from configuration.

    Args:
        pipelines_config: List of pipeline configurations
        llm: Shared OllamaClient instance
        tracker: Shared DigestTracker instance

    Returns:
        List of configured PersonaPipeline instances
    """
    pipelines = []

    for config in pipelines_config:
        if not config.enabled:
            logger.info(f"Pipeline '{config.name}' is disabled, skipping")
            continue

        try:
            pipeline = ConfigurablePipeline(
                pipeline_config=config,
                llm=llm,
                tracker=tracker,
            )
            pipelines.append(pipeline)
            logger.info(f"Created pipeline: {config.name}")
        except Exception as e:
            logger.error(f"Failed to create pipeline '{config.name}': {e}")

    return pipelines
