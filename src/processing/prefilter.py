import logging
from typing import Iterable, Optional, Tuple

from ingestion.base import IngestedItem
from services.digest_tracker import DigestTracker

logger = logging.getLogger(__name__)


def keyword_match(text: str, keywords: Iterable[str]) -> bool:
    text = text.lower()
    return any(k.lower() in text for k in keywords)


def passes_prefilter(
    item: IngestedItem,
    *,
    keywords: Iterable[str],
    min_engagement: float | None = None,
    min_length: int = 200,
) -> bool:
    """Basic prefilter for keyword and engagement checks."""
    content = f"{item.title} {item.content}"

    if len(content) < min_length:
        return False

    if keywords and not keyword_match(content, keywords):
        return False

    if min_engagement is not None:
        if item.engagement_score is None:
            return False
        if item.engagement_score < min_engagement:
            return False

    return True


async def passes_dedup_filter(
    item: IngestedItem,
    tracker: DigestTracker,
) -> Tuple[bool, Optional[str]]:
    """
    Check if item passes deduplication filter.

    Returns:
        Tuple of (passes, duplicate_reason)
        passes is True if item is NOT a duplicate
        duplicate_reason is None if not duplicate, otherwise explains why
    """
    is_dup, reason = await tracker.is_duplicate(
        url=item.url,
        title=item.title,
        content=item.content,
    )

    if is_dup:
        logger.debug(f"Filtered duplicate: {item.title} ({reason})")
        return False, reason

    return True, None


async def filter_duplicates(
    items: list[IngestedItem],
    tracker: DigestTracker,
) -> list[IngestedItem]:
    """
    Filter out duplicate items from a list.

    Returns:
        List of items that are NOT duplicates
    """
    unique_items = []
    seen_urls = set()

    for item in items:
        # Skip if we've already seen this URL in this batch
        if item.url in seen_urls:
            logger.debug(f"Skipping batch duplicate: {item.title}")
            continue

        # Check against database/FAISS
        passes, reason = await passes_dedup_filter(item, tracker)

        if passes:
            unique_items.append(item)
            seen_urls.add(item.url)
        else:
            logger.info(f"Duplicate filtered: {item.title} (reason: {reason})")

    logger.info(f"Dedup filter: {len(items)} -> {len(unique_items)} items")
    return unique_items

