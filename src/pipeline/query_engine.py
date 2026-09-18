"""Shared retrieval, generation, and defended query execution."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.defense.postcheck import CrossEncoderVerifier, verify_retrieval
from src.defense.precheck import check_text
from src.index.embedder import TextEmbedder
from src.index.vector_store import FaissVectorStore

from .prompts import OUTPUT_SCHEMA, build_prompt


@dataclass(frozen=True)
class QueryResult:
    answer: str
    refused: bool
    refusal_reason: str | None
    retrieved: tuple[dict[str, Any], ...]
    timings_ms: dict[str, float]


class OllamaGenerator:
    """Small adapter around the local Ollama chat API."""

    def __init__(self, model: str = "qwen2.5:7b", *, client: Any | None = None) -> None:
        if client is None:
            from ollama import Client

            client = Client()
        self.model = model
        self.client = client

    def generate(self, prompt: str) -> str:
        response = self.client.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            format=OUTPUT_SCHEMA,
            options={"temperature": 0.0},
        )
        return str(response.message.content).strip()


class QueryEngine:
    """Execute baseline or resilient queries against a persisted index."""

    def __init__(
        self,
        index_dir: Path,
        *,
        method: str = "semantic",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        generator: OllamaGenerator | None = None,
        verifier: CrossEncoderVerifier | None = None,
        postcheck_threshold: float = -10.0,
    ) -> None:
        self.index_dir = index_dir
        self.method = method
        self.embedder = TextEmbedder(embedding_model)
        self.store = FaissVectorStore.load(index_dir / f"{method}.faiss")
        metadata_path = index_dir / f"{method}_metadata.jsonl"
        with metadata_path.open("r", encoding="utf-8") as handle:
            self.metadata = [json.loads(line) for line in handle]
        if len(self.metadata) != self.store.size:
            raise ValueError("Index and metadata row counts differ")
        self.generator = generator or OllamaGenerator()
        self.verifier = verifier
        self.postcheck_threshold = postcheck_threshold

    def retrieve(self, query: str, *, top_k: int = 5) -> list[dict[str, Any]]:
        vector = self.embedder.encode([query])
        _, ids = self.store.search(vector, k=top_k)
        return [self.metadata[int(row)] for row in ids[0] if int(row) >= 0]

    def query(self, query: str, *, top_k: int = 5, resilient: bool = False) -> QueryResult:
        timings: dict[str, float] = {}
        start = time.perf_counter()
        retrieved = self.retrieve(query, top_k=top_k)
        timings["retrieve_ms"] = (time.perf_counter() - start) * 1000

        contexts = retrieved
        refusal_reason = None
        if resilient:
            check_start = time.perf_counter()
            accepted = [context for context in contexts if check_text(context["text"]).accepted]
            timings["precheck_ms"] = (time.perf_counter() - check_start) * 1000
            if not accepted:
                refusal_reason = "all retrieved evidence rejected by pre-check"
            elif self.verifier is None:
                refusal_reason = "post-check verifier is not configured"
            else:
                post_start = time.perf_counter()
                postcheck = verify_retrieval(
                    query,
                    accepted,
                    verifier=self.verifier,
                    threshold=self.postcheck_threshold,
                )
                timings["postcheck_ms"] = (time.perf_counter() - post_start) * 1000
                if not postcheck.accepted:
                    refusal_reason = postcheck.reason or "post-check rejected evidence"
                else:
                    contexts = [item.chunk for item in postcheck.ranked_chunks]

        if refusal_reason is not None:
            timings["generation_ms"] = 0.0
            return QueryResult(
                answer="REFUSE_TO_ANSWER: manual review is required.",
                refused=True,
                refusal_reason=refusal_reason,
                retrieved=tuple(retrieved),
                timings_ms=timings,
            )

        generation_start = time.perf_counter()
        answer = self.generator.generate(build_prompt(query, contexts, resilient=resilient))
        timings["generation_ms"] = (time.perf_counter() - generation_start) * 1000
        return QueryResult(
            answer=answer,
            refused=False,
            refusal_reason=None,
            retrieved=tuple(retrieved),
            timings_ms=timings,
        )
