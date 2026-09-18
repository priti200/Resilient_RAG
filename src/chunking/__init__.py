"""Chunking interfaces and implementations."""

from .fixed_size import DEFAULT_MAX_CHARS
from .agentic import OllamaBoundaryAgent
from .model import Chunk

__all__ = ["Chunk", "DEFAULT_MAX_CHARS", "OllamaBoundaryAgent"]
