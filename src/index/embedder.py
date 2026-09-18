"""Sentence-transformer embedding wrapper."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


class TextEmbedder:
    """Encode text batches with a normalized bi-encoder representation."""

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        *,
        device: str | None = None,
    ) -> None:
        from sentence_transformers import SentenceTransformer

        if device is None:
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_name = model_name
        self.device = device
        self.model = SentenceTransformer(model_name, device=device)

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""

        dimension = self.model.get_embedding_dimension()
        if dimension is None:
            raise RuntimeError("Embedding model did not expose a dimension")
        return int(dimension)

    def encode(self, texts: Sequence[str], *, batch_size: int = 64) -> np.ndarray:
        """Encode texts as normalized float32 vectors."""

        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)
        vectors = self.model.encode(
            list(texts),
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype=np.float32)
