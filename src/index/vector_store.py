"""FAISS vector-store wrapper with explicit row ordering."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import faiss
import numpy as np


class FaissVectorStore:
    """Inner-product FAISS index for normalized text embeddings."""

    def __init__(self, dimension: int) -> None:
        if dimension < 1:
            raise ValueError("dimension must be positive")
        self.index = faiss.IndexFlatIP(dimension)

    @property
    def dimension(self) -> int:
        return self.index.d

    @property
    def size(self) -> int:
        return self.index.ntotal

    def add(self, vectors: np.ndarray) -> None:
        """Add normalized float32 vectors to the index."""

        values = np.asarray(vectors, dtype=np.float32)
        if values.ndim != 2 or values.shape[1] != self.dimension:
            raise ValueError(f"Expected vectors with shape (n, {self.dimension})")
        if len(values):
            self.index.add(values)

    def search(self, query_vectors: np.ndarray, k: int = 5) -> tuple[np.ndarray, np.ndarray]:
        """Return scores and row IDs for nearest-neighbor queries."""

        if k < 1:
            raise ValueError("k must be positive")
        queries = np.asarray(query_vectors, dtype=np.float32)
        if queries.ndim != 2 or queries.shape[1] != self.dimension:
            raise ValueError(f"Expected queries with shape (n, {self.dimension})")
        return self.index.search(queries, min(k, self.size))

    def save(self, path: Path) -> None:
        """Persist the FAISS index."""

        path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(path))

    @classmethod
    def load(cls, path: Path) -> "FaissVectorStore":
        """Load a persisted FAISS index."""

        index = faiss.read_index(str(path))
        store = cls(index.d)
        store.index = index
        return store
