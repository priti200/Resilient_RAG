"""Black-box candidate generation using deterministic mutation templates."""

from __future__ import annotations

from typing import Any

from .templates import PAYLOADS


def generate_candidates(
    record: dict[str, Any],
    *,
    goal: str,
    target_query: str,
    limit: int = 4,
) -> list[dict[str, Any]]:
    """Generate payload candidates without using model internals."""

    if limit < 1:
        raise ValueError("limit must be at least 1")
    payloads = PAYLOADS[goal][:limit]
    return [
        {
            "source_record_id": str(record["id"]),
            "goal": goal,
            "target_query": target_query,
            "instruction": payload,
            "attack_type": "black_box",
            "candidate_rank": rank,
        }
        for rank, payload in enumerate(payloads, start=1)
    ]
