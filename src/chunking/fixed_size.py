"""Fixed-size character-window chunking for flow JSONL records."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Iterator

from .common import record_fields, unique_in_order
from .model import Chunk


DEFAULT_MAX_CHARS = 2048
SEPARATOR = "\n\n"


def chunk_records(
    records: Iterable[Mapping[str, Any]],
    *,
    split_name: str = "data",
    max_chars: int = DEFAULT_MAX_CHARS,
) -> Iterator[Chunk]:
    """Yield fixed-size windows while retaining source-flow provenance.

    Windows intentionally ignore flow boundaries. A source flow can therefore
    span multiple chunks, and a chunk can contain portions of multiple flows.
    ``source_flow_ids`` records that contamination explicitly for evaluation.
    """

    if max_chars < 1:
        raise ValueError("max_chars must be at least 1")

    buffer = ""
    spans: list[tuple[int, int, str, str | None]] = []
    chunk_position = 0

    for record in records:
        record_id, text, label = record_fields(record)
        segment = text + SEPARATOR
        segment_start = len(buffer)
        buffer += segment
        spans.append((segment_start, segment_start + len(text), record_id, label))

        while len(buffer) >= max_chars:
            window_end = max_chars
            source_ids = [
                source_id
                for start, end, source_id, _ in spans
                if start < window_end and end > 0
            ]
            source_labels = [
                label
                for start, end, _, label in spans
                if start < window_end and end > 0 and label is not None
            ]
            chunk_position += 1
            yield Chunk(
                chunk_id=f"{split_name}_fixed_{chunk_position:08d}",
                text=buffer[:window_end],
                method="fixed",
                source_flow_ids=unique_in_order(source_ids),
                source_labels=unique_in_order(source_labels),
                metadata={"max_chars": max_chars},
            )

            buffer = buffer[window_end:]
            spans = [
                (start - window_end, end - window_end, source_id, label)
                for start, end, source_id, label in spans
                if end > window_end
            ]

    if buffer:
        source_ids = [source_id for _, _, source_id, _ in spans]
        source_labels = [label for _, _, _, label in spans if label is not None]
        chunk_position += 1
        yield Chunk(
            chunk_id=f"{split_name}_fixed_{chunk_position:08d}",
            text=buffer,
            method="fixed",
            source_flow_ids=unique_in_order(source_ids),
            source_labels=unique_in_order(source_labels),
            metadata={"max_chars": max_chars},
        )
