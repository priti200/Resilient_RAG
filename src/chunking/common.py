"""Common validation and metadata helpers for chunkers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def record_fields(record: Mapping[str, Any]) -> tuple[str, str, str | None]:
    """Extract and validate the ID, text, and optional label from a JSONL record."""

    if "id" not in record:
        raise ValueError("Each flow record must contain an 'id' field")
    if "text" not in record:
        raise ValueError("Each flow record must contain a 'text' field")

    record_id = str(record["id"])
    text = record["text"]
    if not isinstance(text, str) or not text:
        raise ValueError(f"Flow record {record_id!r} has empty or non-string text")

    label = record.get("label")
    if label is None and isinstance(record.get("metadata"), Mapping):
        label = record["metadata"].get("CategoryLabel")
    return record_id, text, str(label) if label is not None else None


def unique_in_order(values: list[str]) -> tuple[str, ...]:
    """Remove duplicate provenance values while preserving source order."""

    return tuple(dict.fromkeys(values))
