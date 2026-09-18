"""Unit tests for post-retrieval verification."""

from src.defense.postcheck import CrossEncoderVerifier, verify_retrieval


class FakeCrossEncoder:
    def predict(self, pairs):
        return [0.2, 0.9][: len(pairs)]


def test_postcheck_reranks_and_accepts() -> None:
    chunks = [{"chunk_id": "a", "text": "weak"}, {"chunk_id": "b", "text": "strong"}]
    result = verify_retrieval(
        "query",
        chunks,
        verifier=CrossEncoderVerifier(model=FakeCrossEncoder()),
        threshold=0.5,
    )

    assert result.accepted is True
    assert result.ranked_chunks[0].chunk["chunk_id"] == "b"


def test_postcheck_refuses_low_score() -> None:
    result = verify_retrieval(
        "query",
        [{"chunk_id": "a", "text": "weak"}],
        verifier=CrossEncoderVerifier(model=FakeCrossEncoder()),
        threshold=0.5,
    )

    assert result.accepted is False
    assert result.reason == "top evidence below threshold"
