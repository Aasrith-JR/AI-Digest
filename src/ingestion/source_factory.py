"""
Source Factory - Creates ingestion adapters from configuration.
"""
import logging
from typing import List

from ingestion.base import SourceAdapter
from ingestion.reddit import RedditAdapter
from ingestion.rss import RSSAdapter
from ingestion.hackernews import HackerNewsAdapter
from ingestion.producthunt import ProductHuntAdapter
from services.config import SourceConfig, IngestionConfig, get_enabled_sources

logger = logging.getLogger(__name__)


def create_source_adapter(source_config: SourceConfig) -> SourceAdapter:
    """
    Create a source adapter from configuration.

    Args:
        source_config: Configuration for the source

    Returns:
        Configured SourceAdapter instance

    Raises:
        ValueError: If source type is unknown
    """
    source_type = source_config.type.lower()

    if source_type == "reddit":
        if not source_config.subreddit:
            raise ValueError("Reddit source requires 'subreddit' field")
        return RedditAdapter(source_config.subreddit)

    elif source_type == "rss":
        if not source_config.feeds:
            raise ValueError("RSS source requires 'feeds' field")
        return RSSAdapter(
            feed_urls=source_config.feeds,
            source_name=source_config.name or "rss",
        )

    elif source_type == "hackernews":
        return HackerNewsAdapter()

    elif source_type == "producthunt":
        return ProductHuntAdapter()

    else:
        raise ValueError(f"Unknown source type: {source_type}")


def create_adapters_from_config(ingestion_config: IngestionConfig) -> List[SourceAdapter]:
    """
    Create all enabled source adapters from ingestion configuration.

    Args:
        ingestion_config: Ingestion configuration with sources

    Returns:
        List of configured SourceAdapter instances
    """
    adapters = []
    enabled_sources = get_enabled_sources(ingestion_config)

    for source_config in enabled_sources:
        try:
            adapter = create_source_adapter(source_config)
            adapters.append(adapter)
            logger.info(f"Created {source_config.type} adapter: {source_config.subreddit or source_config.name or 'default'}")
        except Exception as e:
            logger.error(f"Failed to create adapter for {source_config.type}: {e}")

    return adapters
