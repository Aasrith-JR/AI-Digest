# src/workflows/genai_news.py
from typing import List

from core.entities import DigestEntry
from core.personas import GENAI_NEWS
from ingestion.hackernews import HackerNewsAdapter
from ingestion.reddit import RedditAdapter
from ingestion.rss import RSSAdapter
from processing.prefilter import passes_prefilter
from processing.summarizer import summarize_cluster
from workflows.base import PersonaPipeline


class GenAINewsPipeline(PersonaPipeline):
    name = GENAI_NEWS.name

    def __init__(self):
        self.sources = [
            # HackerNewsAdapter(),
            RedditAdapter("MachineLearning"),
            RedditAdapter("LocalLLaMA"),
            RSSAdapter(
                feed_urls=[
                    "https://www.lesswrong.com/feed.xml",
                    "https://www.semianalysis.com/feed",
                ],
                source_name="genai_rss",
            ),
        ]

        self.keywords = [
            "llm",
            "transformer",
            "inference",
            "quantization",
            "agents",
            "ollama",
            "faiss",
            "gpu",
        ]

    async def run(self) -> List[DigestEntry]:
        digest_entries: List[DigestEntry] = []

        try:
            items = []
            for source in self.sources:
                items.extend(await source.fetch_items(hours=24))

            for item in items:
                if not passes_prefilter(
                    item,
                    keywords=self.keywords,
                    min_engagement=5,
                ):
                    continue

                # Placeholder summary until LLM stage is wired
                entry = summarize_cluster(
                    persona=GENAI_NEWS,
                    title=item.title,
                    summary=item.content[:400],
                    why_it_matters="Relevant update in the GenAI ecosystem.",
                    audience="developer",
                    source_urls=[item.url],
                    structured_output={"relevance_score": 0.7},
                )

                digest_entries.append(entry)

        except Exception:
            return []

        return sorted(
            digest_entries,
            key=lambda e: e.score,
            reverse=True,
        )[:10]
