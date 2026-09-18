"""Post-retrieval cross-encoder verification and safe refusal."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence


@dataclass(frozen=True)
class RerankedChunk:
    chunk: dict[str, Any]
    score: float


@dataclass(frozen=True)
class PostcheckResult:
    accepted: bool
    ranked_chunks: tuple[RerankedChunk, ...]
    reason: str | None = None


class CrossEncoderVerifier:
    """Cross-encoder wrapper with lazy model loading."""

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        *,
        device: str | None = None,
        model: Any | None = None,
    ) -> None:
        if model is None:
            from sentence_transformers import CrossEncoder

            model = CrossEncoder(model_name, device=device)
        self.model = model
        self.model_name = model_name

    def rerank(self, query: str, chunks: Sequence[dict[str, Any]]) -> list[RerankedChunk]:
        if not chunks:
            return []
        scores = self.model.predict([(query, chunk["text"]) for chunk in chunks])
        ranked = sorted(
            (RerankedChunk(chunk=chunk, score=float(score)) for chunk, score in zip(chunks, scores)),
            key=lambda item: item.score,
            reverse=True,
        )
        return ranked


def verify_retrieval(
    query: str,
    chunks: Sequence[dict[str, Any]],
    *,
    verifier: CrossEncoderVerifier,
    threshold: float,
    flagged_chunk_ids: set[str] | None = None,
) -> PostcheckResult:
    """Re-rank candidates and refuse when evidence is weak or flagged."""

    ranked = verifier.rerank(query, chunks)
    if not ranked:
        return PostcheckResult(False, (), "no retrieved evidence")
    top = ranked[0]
    if top.score < threshold:
        return PostcheckResult(False, tuple(ranked), "top evidence below threshold")
    if flagged_chunk_ids and top.chunk.get("chunk_id") in flagged_chunk_ids:
        return PostcheckResult(False, tuple(ranked), "top evidence flagged by pre-check")
    return PostcheckResult(True, tuple(ranked))
