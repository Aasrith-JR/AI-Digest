from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass(frozen=True)
class Item:
    """
    Canonical representation of an ingested content item.
    """
    id: int
    persona: str
    source: str
    title: str
    content: str
    url: str
    published_at: Optional[datetime]
    engagement_score: Optional[float]


@dataclass(frozen=True)
class Evaluation:
    """
    Result of LLM evaluation for an item.
    """
    item_id: int
    persona: str
    relevance_score: float
    decision: str
    structured_output: Dict[str, Any]


@dataclass
class Cluster:
    """
    Group of semantically similar items.
    """
    id: int
    persona: str
    representative_item_id: int
    item_ids: List[int] = field(default_factory=list[int])


@dataclass(frozen=True)
class DigestEntry:
    """
    Final digest-ready unit of information.
    """
    title: str
    summary: str
    why_it_matters: str
    audience: str
    source_urls: List[str]
    score: float
