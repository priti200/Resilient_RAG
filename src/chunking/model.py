"""Shared data model for chunking outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class Chunk:
    """A searchable text unit and its source-flow provenance."""

    chunk_id: str
    text: str
    method: str
    source_flow_ids: tuple[str, ...]
    source_labels: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the chunk."""

        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "method": self.method,
            "source_flow_ids": list(self.source_flow_ids),
            "source_labels": list(self.source_labels),
            "metadata": dict(self.metadata),
        }
