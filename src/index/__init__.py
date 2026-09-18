"""Embedding and vector-index components."""

from .embedder import TextEmbedder
from .vector_store import FaissVectorStore

__all__ = ["FaissVectorStore", "TextEmbedder"]
