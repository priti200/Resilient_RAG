"""Semantic-boundary chunking for flow JSONL records."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Iterator

from .common import record_fields
from .model import Chunk


def chunk_records(
    records: Iterable[Mapping[str, Any]],
    *,
    split_name: str = "data",
) -> Iterator[Chunk]:
    """Yield one chunk per flow record without mixing neighboring flows."""

    for position, record in enumerate(records, start=1):
        record_id, text, label = record_fields(record)
        labels = (label,) if label is not None else ()
        yield Chunk(
            chunk_id=f"{split_name}_semantic_{position:08d}",
            text=text,
            method="semantic",
            source_flow_ids=(record_id,),
            source_labels=labels,
            metadata={"source_position": position},
        )
