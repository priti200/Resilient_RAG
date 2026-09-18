"""Baseline pipeline facade."""

from __future__ import annotations

from .query_engine import QueryEngine, QueryResult


def run_baseline(engine: QueryEngine, query: str, *, top_k: int = 5) -> QueryResult:
    """Run the undefended pipeline."""

    return engine.query(query, top_k=top_k, resilient=False)
