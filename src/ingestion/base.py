"""
Base classes for Ingestion
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class IngestedItem(BaseModel):
    """
    dataclass for IngestedItem 
    """
    source: str
    external_id: Optional[str]
    title: str
    content: str
    url: str
    published_at: Optional[datetime]
    engagement_score: Optional[float]


class SourceAdapter(ABC):
    """
    Base interface for all ingestion sources.
    """

    @abstractmethod
    async def fetch_items(self, hours: int) -> List[IngestedItem]:
        """
        Fetch items published within the last N hours.
        Must NEVER raise uncaught exceptions.
        """
        raise NotImplementedError
