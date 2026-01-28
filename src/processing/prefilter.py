from typing import Iterable

from ingestion.base import IngestedItem


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
