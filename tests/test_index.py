"""Unit tests for the FAISS vector store."""

from __future__ import annotations

import numpy as np
import pytest

from src.index.vector_store import FaissVectorStore


def test_faiss_store_search_and_round_trip(tmp_path) -> None:
    store = FaissVectorStore(2)
    store.add(np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32))
    scores, ids = store.search(np.asarray([[0.9, 0.1]], dtype=np.float32), k=2)

    assert store.size == 2
    assert ids[0].tolist() == [0, 1]
    assert scores[0, 0] > scores[0, 1]

    path = tmp_path / "test.faiss"
    store.save(path)
    loaded = FaissVectorStore.load(path)
    assert loaded.size == 2
    assert loaded.dimension == 2


def test_faiss_store_validates_inputs() -> None:
    store = FaissVectorStore(2)
    with pytest.raises(ValueError, match="shape"):
        store.add(np.asarray([[1.0, 0.0, 0.0]], dtype=np.float32))
    with pytest.raises(ValueError, match="positive"):
        store.search(np.asarray([[1.0, 0.0]], dtype=np.float32), k=0)
