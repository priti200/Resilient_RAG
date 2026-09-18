"""White-box candidate ranking using the known retrieval encoder."""

from __future__ import annotations

from typing import Any

import numpy as np


def rank_candidates(
    target_query: str,
    candidates: list[dict[str, Any]],
    *,
    embedder: Any,
) -> list[dict[str, Any]]:
    """Rank candidate instructions by target-query embedding similarity."""

    if not candidates:
        return []
    texts = [str(candidate["instruction"]) for candidate in candidates]
    query_vector = np.asarray(embedder.encode([target_query])[0], dtype=np.float32)
    candidate_vectors = np.asarray(embedder.encode(texts), dtype=np.float32)
    scores = np.asarray(candidate_vectors @ query_vector, dtype=np.float32)
    ranked = []
    for rank, (score, candidate) in enumerate(
        sorted(zip(scores.tolist(), candidates), key=lambda item: item[0], reverse=True),
        start=1,
    ):
        item = dict(candidate)
        item["attack_type"] = "white_box"
        item["retrieval_similarity"] = round(float(score), 6)
        item["candidate_rank"] = rank
        ranked.append(item)
    return ranked
