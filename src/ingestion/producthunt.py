"""
Get feed from ProductHunt
"""
from ingestion.rss import RSSAdapter

class ProductHuntAdapter(RSSAdapter):
    def __init__(self):
        super().__init__(
            feed_urls=["https://www.producthunt.com/feed"],
            source_name="producthunt",
        )
