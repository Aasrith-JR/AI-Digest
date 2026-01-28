from typing import List, Tuple

from services.vector_store import VectorStore


def is_duplicate(
    *,
    vector_store: VectorStore,
    embedding: List[float],
    similarity_threshold: float = 0.85,
) -> Tuple[bool, int | None]:
    """
    Returns (is_duplicate, existing_faiss_id)
    """
    results = vector_store.search(embedding, k=3)

    for idx, score in results:
        if idx == -1:
            continue
        if score >= similarity_threshold:
            return True, idx

    return False, None
