"""
Module to contain base class for Delivery channels
"""
from abc import ABC, abstractmethod
from typing import List

from core.entities import DigestEntry


class DeliveryChannel(ABC):
    """
    Base interface for all delivery channels.
    """

    name: str

    @abstractmethod
    async def deliver(
        self,
        *,
        persona: str,
        digest_date: str,
        entries: List[DigestEntry],
    ) -> None:
        """
        Deliver the digest.
        Must raise exceptions on failure (handled upstream).
        """
        raise NotImplementedError
