import faiss
import os
import numpy as np
from typing import List, Tuple


class VectorStore:
    def __init__(self, path: str, dim: int = 384):
        self.path = path
        self.dim = dim

        if os.path.exists(path):
            self.index = faiss.read_index(path)
        else:
            self.index = faiss.IndexFlatIP(dim)

    def add(self, vector: List[float]) -> int:
        vec = np.array([vector]).astype("float32")
        faiss.normalize_L2(vec)
        idx = self.index.ntotal
        self.index.add(vec)
        return idx

    def search(self, vector: List[float], k: int = 5) -> List[Tuple[int, float]]:
        vec = np.array([vector]).astype("float32")
        faiss.normalize_L2(vec)
        scores, indices = self.index.search(vec, k)
        return list(zip(indices[0].tolist(), scores[0].tolist()))

    def persist(self) -> None:
        faiss.write_index(self.index, self.path)
