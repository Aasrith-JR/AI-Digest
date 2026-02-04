# src/workflows/genai_news.py
import logging
from typing import List, Optional

from core.entities import DigestEntry
from core.personas import GENAI_NEWS
from ingestion.source_factory import create_adapters_from_config
from processing.prefilter import passes_prefilter, filter_duplicates
from processing.summarizer import summarize_cluster
from processing.evaluator import evaluate_batch
from services.llm import OllamaClient
from services.config import load_config
from services.database import Database
from services.vector_store import VectorStore
from services.digest_tracker import DigestTracker
from workflows.base import PersonaPipeline

logger = logging.getLogger(__name__)


class GenAINewsPipeline(PersonaPipeline):
    name = GENAI_NEWS.name

    def __init__(
        self,
        llm: Optional[OllamaClient] = None,
        tracker: Optional[DigestTracker] = None,
    ):
        config = load_config()
        self.config = config

        self.llm = llm or OllamaClient(
            base_url=config.OLLAMA_BASE_URL,
            model=config.OLLAMA_MODEL,
        )

        # Initialize tracker for deduplication
        if tracker:
            self.tracker = tracker
        else:
            db = Database(config.DATABASE_PATH)
            vector_store = VectorStore(config.FAISS_INDEX_PATH)
            self.tracker = DigestTracker(db, vector_store)

        # Load sources from config
        if config.ingestion_genai_news:
            self.sources = create_adapters_from_config(config.ingestion_genai_news)
            self.keywords = config.ingestion_genai_news.keywords
            self.min_engagement = config.ingestion_genai_news.min_engagement
            self.top_k = config.ingestion_genai_news.top_k
        else:
            # Fallback defaults
            logger.warning("No ingestion config found for genai_news, using defaults")
            self.sources = []
            self.keywords = ["llm", "transformer", "inference", "quantization", "agents"]
            self.min_engagement = 5
            self.top_k = 5

    async def run(self) -> List[DigestEntry]:
        digest_entries: List[DigestEntry] = []

        try:
            # Fetch all items from sources
            items = []
            for source in self.sources:
                items.extend(await source.fetch_items(hours=24))

            logger.info(f"Fetched {len(items)} items from sources")

            # Pre-filter items by keywords and engagement
            filtered_items = []
            for item in items:
                if passes_prefilter(
                    item,
                    keywords=self.keywords,
                    min_engagement=self.min_engagement,
                ):
                    filtered_items.append(item)

            logger.info(f"After keyword filter: {len(filtered_items)} items")

            if not filtered_items:
                logger.info("No items passed pre-filter")
                return []

            # Deduplication: Remove items already sent within 48 hours
            unique_items = await filter_duplicates(filtered_items, self.tracker)

            if not unique_items:
                logger.info("No unique items after deduplication")
                return []

            logger.info(f"After deduplication: {len(unique_items)} unique items")

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

            logger.info(f"Sending {len(batch_items)} items for evaluation (selecting top {self.top_k})")

            # Single LLM call for all items - returns top_k
            try:
                evaluations = await evaluate_batch(
                    llm=self.llm,
                    persona=GENAI_NEWS,
                    items=batch_items,
                    top_k=self.top_k,
                )
            except Exception as eval_error:
                logger.error(f"Batch evaluation failed: {eval_error}")
                return []

            # Process results - only the selected top items
            for eval_result in evaluations:
                item_id = eval_result["id"]
                try:
                    item_idx = int(item_id)
                    item = unique_items[item_idx]
                except (ValueError, IndexError):
                    logger.warning(f"Invalid item ID from LLM: {item_id}")
                    continue

                parsed = eval_result.get("parsed")
                if not parsed:
                    continue

                relevance_score = parsed.get("relevance_score", 0.0)

                entry = summarize_cluster(
                    persona=GENAI_NEWS,
                    title=item.title,
                    summary=item.content[:400],
                    why_it_matters=parsed.get("why_it_matters", "Relevant update in the GenAI ecosystem."),
                    audience=parsed.get("target_audience", "developer"),
                    source_urls=[item.url],
                    structured_output=parsed,
                )

                digest_entries.append(entry)

                # Record sent digest for future deduplication
                await self.tracker.record_sent_digest(
                    url=item.url,
                    title=item.title,
                    persona=GENAI_NEWS.name,
                    relevance_score=relevance_score,
                    content=item.content,
                )

                logger.info(f"Included item: {item.title} (score: {relevance_score})")

        except Exception as e:
            logger.exception(f"Pipeline error: {e}")
            return []

        # Return top_k items, already sorted by LLM
        return digest_entries[:self.top_k]
