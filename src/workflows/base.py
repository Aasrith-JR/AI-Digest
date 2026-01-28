"""
Contains base class for Personas
"""
from abc import ABC, abstractmethod
from typing import List

from core.entities import DigestEntry


class PersonaPipeline(ABC):
    """
    Orchestrates ingestion → processing → summarization
    for a single persona.
    """

    name: str

    @abstractmethod
    async def run(self) -> List[DigestEntry]:
        """
        Execute the persona pipeline and return digest entries.
        Must never raise uncaught exceptions.
        """
        raise NotImplementedError
