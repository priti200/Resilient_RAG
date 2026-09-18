# Chunking Strategies

The project evaluates three chunking strategies over the deterministic flow
JSONL representation.

## Semantic

One flow record becomes one chunk. This is the strongest isolation baseline:
one poisoned flow cannot share a chunk with a neighboring flow.

## Fixed-size

The concatenated flow text is divided into 2,048-character windows without
respecting flow boundaries. Each chunk retains source-flow provenance so the
experiment can measure cross-flow contamination.

## Agentic

The local Ollama model decides whether each adjacent pair of flows belongs in
the same retrieval unit. Agentic decisions are constrained by:

- `max_records`: maximum flows in one chunk.
- `max_chars`: maximum chunk text size.
- Adjacent-only grouping; the agent cannot reorder records.
- JSON-only decisions with a strict boolean `same_chunk` field.
- Fail-closed fallback: invalid, unavailable, or failed decisions start a new
  chunk.

The agentic strategy is therefore an LLM-assisted grouping policy, not an
unbounded autonomous rewrite of the dataset. Every output records its method,
source-flow IDs, limits, and fallback-decision count.

## Verification

The implementation is in `src/chunking/`. Unit tests use an injected fake
boundary decider, while the smoke test verifies the real `qwen2.5:7b` Ollama
path on two flow records. The comparison script reports multi-flow chunks and
maximum flows per chunk for bounded samples.
