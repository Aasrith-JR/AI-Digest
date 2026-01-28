# src/workflows/product_ideas.py
from typing import List

from core.entities import DigestEntry
from core.personas import PRODUCT_IDEAS
from ingestion.producthunt import ProductHuntAdapter
from ingestion.reddit import RedditAdapter
from ingestion.subreddit import SubReddit
from processing.prefilter import passes_prefilter
from processing.summarizer import summarize_cluster
from workflows.base import PersonaPipeline
from asyncpraw import Reddit


class ProductIdeasPipeline(PersonaPipeline):
    name = PRODUCT_IDEAS.name

    def __init__(self):
        self.sources = [
            ProductHuntAdapter(),
            RedditAdapter("SideProject"),
        ]

        self.keywords = [
            "launched",
            "built",
            "mvp",
            "experiment",
            "users",
            "revenue",
            "problem",
            "pain",
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
                    min_engagement=3,
                ):
                    continue

                entry = summarize_cluster(
                    persona=PRODUCT_IDEAS,
                    title=item.title,
                    summary=item.content[:400],
                    why_it_matters="Potential product opportunity or unmet need.",
                    audience="founder",
                    source_urls=[item.url],
                    structured_output={"reusability_score": 0.6},
                )

                digest_entries.append(entry)

        except Exception:
            return []

        return sorted(
            digest_entries,
            key=lambda e: e.score,
            reverse=True,
        )[:10]
