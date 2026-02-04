"""
DigestTracker - Combines SQL database and FAISS for deduplication.
Tracks sent digests and checks for similar content using semantic embeddings.
"""
import hashlib
import logging
from typing import List, Optional, Tuple

from services.database import Database
from services.vector_store import VectorStore

logger = logging.getLogger(__name__)


def simple_embedding(text: str, dim: int = 384) -> List[float]:
    """
    Generate a simple hash-based embedding for text.
    This is a lightweight alternative to using a full embedding model.
    For production, consider using sentence-transformers or similar.
    """
    # Normalize text
    text = text.lower().strip()

    # Create multiple hash variations for better distribution
    embeddings = []
    for i in range(dim):
        # Create a unique hash for each dimension
        hash_input = f"{text}_{i}"
        hash_bytes = hashlib.sha256(hash_input.encode()).digest()
        # Convert to float in range [-1, 1]
        value = (int.from_bytes(hash_bytes[:4], 'big') / (2**32)) * 2 - 1
        embeddings.append(value)

    return embeddings


def text_to_embedding(title: str, content: str = "", dim: int = 384) -> List[float]:
    """
    Convert title and content to an embedding vector.
    Combines title (weighted higher) with content preview.
    """
    # Weight title more heavily by repeating it
    combined_text = f"{title} {title} {content[:200]}"
    return simple_embedding(combined_text, dim)


class DigestTracker:
    """
    Tracks sent digests using both SQL (for exact URL matching)
    and FAISS (for semantic similarity).
    """

    def __init__(
        self,
        database: Database,
        vector_store: VectorStore,
        similarity_threshold: float = 0.85,
        dedup_hours: int = 48,
    ):
        self.db = database
        self.vector_store = vector_store
        self.similarity_threshold = similarity_threshold
        self.dedup_hours = dedup_hours
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the database tables."""
        if not self._initialized:
            await self.db.init_tables()
            self._initialized = True

    async def is_duplicate(
        self,
        url: str,
        title: str,
        content: str = "",
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if an item is a duplicate.

        Returns:
            Tuple of (is_duplicate, reason)
            reason is None if not duplicate, otherwise explains why
        """
        await self.initialize()

        # Check 1: Exact URL match
        if await self.db.is_url_sent(url, hours=self.dedup_hours):
            logger.debug(f"Duplicate URL found: {url}")
            return True, "exact_url_match"

        # Check 2: Semantic similarity using FAISS
        if self.vector_store.index.ntotal > 0:
            embedding = text_to_embedding(title, content)

            # Get IDs of recently sent digests
            recent_faiss_ids = await self.db.get_recent_faiss_ids(hours=self.dedup_hours)

            if recent_faiss_ids:
                # Search for similar items
                results = self.vector_store.search(embedding, k=min(10, self.vector_store.index.ntotal))

                for faiss_id, score in results:
                    if faiss_id == -1:
                        continue
                    # Only consider as duplicate if it's in recent digests
                    if faiss_id in recent_faiss_ids and score >= self.similarity_threshold:
                        logger.debug(f"Similar content found: {title} (score: {score:.3f})")
                        return True, f"similar_content_{score:.3f}"

        return False, None

    async def record_sent_digest(
        self,
        url: str,
        title: str,
        persona: str,
        relevance_score: Optional[float] = None,
        content: str = "",
    ) -> int:
        """
        Record a sent digest in both SQL and FAISS.

        Returns:
            The database ID of the recorded digest
        """
        await self.initialize()

        # Add to FAISS
        embedding = text_to_embedding(title, content)
        faiss_id = self.vector_store.add(embedding)

        # Add to database
        db_id = await self.db.add_sent_digest(
            url=url,
            title=title,
            persona=persona,
            relevance_score=relevance_score,
            faiss_id=faiss_id,
        )

        # Persist FAISS index
        self.vector_store.persist()

        logger.debug(f"Recorded digest: {title} (db_id={db_id}, faiss_id={faiss_id})")
        return db_id

    async def get_recent_digests(
        self,
        hours: int = 48,
        persona: Optional[str] = None,
    ) -> List[Tuple[int, str, str, float, str]]:
        """Get recently sent digests."""
        await self.initialize()
        return await self.db.get_recent_digests(hours=hours, persona=persona)

    async def cleanup(self, days: int = 30) -> int:
        """Remove old digest records."""
        await self.initialize()
        count = await self.db.cleanup_old_digests(days=days)
        logger.info(f"Cleaned up {count} old digest records")
        return count
