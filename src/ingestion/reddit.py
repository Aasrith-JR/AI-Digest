import httpx
from datetime import datetime, timedelta
from typing import List

from ingestion.base import SourceAdapter, IngestedItem

class RedditAdapter(SourceAdapter):
    def __init__(self, subreddit: str):
        self.subreddit = subreddit

    async def fetch_items(self, hours: int) -> List[IngestedItem]:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        items: List[IngestedItem] = []

        headers = {"User-Agent": "local-intel-digest/1.0"}

        try:
            async with httpx.AsyncClient(timeout=30, headers=headers) as client:
                resp = await client.get(
                    f"https://www.reddit.com/r/{self.subreddit}/new.json?limit=50"
                )
                resp.raise_for_status()

                posts = resp.json()["data"]["children"]

                for post in posts:
                    data = post["data"]
                    published = datetime.utcfromtimestamp(
                        data.get("created_utc", 0))
                    if published < cutoff:
                        continue

                    items.append(
                        IngestedItem(
                            source=f"reddit/{self.subreddit}",
                            external_id=data.get("id"),
                            title=data.get("title", ""),
                            content=data.get("selftext", ""),
                            url=f"https://reddit.com{data.get('permalink', '')}",
                            published_at=published,
                            engagement_score=float(data.get("score", 0)),
                        )
                    )

        except Exception:
            return []

        return items
