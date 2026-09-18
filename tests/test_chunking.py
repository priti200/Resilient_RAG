"""Unit tests for semantic and fixed-size chunking."""

from __future__ import annotations

import pytest

from src.chunking.fixed_size import chunk_records as fixed_chunks
from src.chunking.agentic import chunk_records as agentic_chunks
from src.chunking.semantic import chunk_records as semantic_chunks


def _records() -> list[dict[str, object]]:
    return [
        {"id": "flow-1", "text": "A" * 7, "label": "benign"},
        {"id": "flow-2", "text": "B" * 7, "label": "dos"},
        {"id": "flow-3", "text": "C" * 7, "label": "recon"},
    ]


def test_semantic_chunking_keeps_one_flow_per_chunk() -> None:
    chunks = list(semantic_chunks(_records(), split_name="test"))

    assert len(chunks) == 3
    assert [chunk.source_flow_ids for chunk in chunks] == [
        ("flow-1",),
        ("flow-2",),
        ("flow-3",),
    ]
    assert all(chunk.method == "semantic" for chunk in chunks)


def test_semantic_chunk_ids_are_deterministic() -> None:
    first = [chunk.to_dict() for chunk in semantic_chunks(_records(), split_name="test")]
    second = [chunk.to_dict() for chunk in semantic_chunks(_records(), split_name="test")]

    assert first == second


def test_fixed_chunking_obeys_maximum_size() -> None:
    chunks = list(fixed_chunks(_records(), split_name="test", max_chars=10))

    assert chunks
    assert all(0 < len(chunk.text) <= 10 for chunk in chunks)
    assert all(chunk.method == "fixed" for chunk in chunks)


def test_fixed_chunking_tracks_cross_flow_contamination() -> None:
    chunks = list(fixed_chunks(_records(), split_name="test", max_chars=10))

    assert any(len(chunk.source_flow_ids) > 1 for chunk in chunks)
    assert {flow_id for chunk in chunks for flow_id in chunk.source_flow_ids} == {
        "flow-1",
        "flow-2",
        "flow-3",
    }


def test_fixed_chunking_rejects_invalid_size() -> None:
    with pytest.raises(ValueError, match="max_chars"):
        list(fixed_chunks(_records(), max_chars=0))


def test_chunking_rejects_missing_text() -> None:
    with pytest.raises(ValueError, match="text"):
        list(semantic_chunks([{"id": "missing-text"}]))


def test_agentic_chunking_groups_adjacent_related_flows() -> None:
    decisions = iter([True, False])
    chunks = list(
        agentic_chunks(
            _records(),
            boundary_decider=lambda _previous, _current: next(decisions),
            split_name="test",
        )
    )

    assert [chunk.source_flow_ids for chunk in chunks] == [
        ("flow-1", "flow-2"),
        ("flow-3",),
    ]
    assert chunks[0].method == "agentic"


def test_agentic_chunking_fails_closed_when_agent_errors() -> None:
    def failing_decider(_previous: str, _current: str) -> bool:
        raise RuntimeError("agent unavailable")

    chunks = list(
        agentic_chunks(
            _records(),
            boundary_decider=failing_decider,
            split_name="test",
        )
    )

    assert [chunk.source_flow_ids for chunk in chunks] == [
        ("flow-1",),
        ("flow-2",),
        ("flow-3",),
    ]
    assert [chunk.metadata["fallback_decisions"] for chunk in chunks] == [1, 1, 0]


def test_agentic_chunking_enforces_hard_limits() -> None:
    chunks = list(
        agentic_chunks(
            _records(),
            boundary_decider=lambda _previous, _current: True,
            max_records=2,
            max_chars=20,
        )
    )

    assert all(len(chunk.source_flow_ids) <= 2 for chunk in chunks)
    assert all(len(chunk.text) <= 20 for chunk in chunks)
