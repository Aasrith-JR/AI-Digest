"""
Ingest data from Hackernew
"""

from datetime import datetime, timedelta
from logging import Logger
from typing import List
import httpx


from ingestion.base import SourceAdapter, IngestedItem


class HackerNewsAdapter(SourceAdapter):
    BASE_URL = "https://hacker-news.firebaseio.com/v0"

    async def fetch_items(self, hours: int) -> List[IngestedItem]:
        cutoff = datetime.now() - timedelta(hours=hours)
        items: List[IngestedItem] = []

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(f"{self.BASE_URL}/newstories.json")
                resp.raise_for_status()

                story_ids = resp.json()[:200]

                for sid in story_ids:
                    story = await client.get(f"{self.BASE_URL}/item/{sid}.json")
                    if story.status_code != 200:
                        continue

                    data = story.json()
                    if not data or data.get("type") != "story":
                        continue

                    published = datetime.fromtimestamp(data.get("time", 0))
                    if published < cutoff:
                        continue

                    items.append(
                        IngestedItem(
                            source="hackernews",
                            external_id=str(sid),
                            title=data.get("title", ""),
                            content=data.get("text", "") or "",
                            url=data.get("url", ""),
                            published_at=published,
                            engagement_score=float(data.get("score", 0)),
                        )
                    )


        except Exception:
            # Fail silently; error is logged upstream
            return []

        return items
