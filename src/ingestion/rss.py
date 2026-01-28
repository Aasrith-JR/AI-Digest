"""
Ingestion from RSS sources
"""

from datetime import datetime, timedelta
from typing import List
import feedparser

from ingestion.base import SourceAdapter, IngestedItem


class RSSAdapter(SourceAdapter):
    def __init__(self, feed_urls: List[str], source_name: str):
        self.feed_urls = feed_urls
        self.source_name = source_name

    async def fetch_items(self, hours: int) -> List[IngestedItem]:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        items: List[IngestedItem] = []

        for url in self.feed_urls:
            try:
                feed = feedparser.parse(url)

                for entry in feed.entries:
                    published = None
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        published = datetime(*entry.published_parsed[:6])

                    if published and published < cutoff:
                        continue

                    items.append(
                        IngestedItem(
                            source=self.source_name,
                            external_id=entry.get("id"),
                            title=entry.get("title", ""),
                            content=entry.get("summary", ""),
                            url=entry.get("link", ""),
                            published_at=published,
                            engagement_score=None,
                        )
                    )

            except Exception:
                continue

        return items
