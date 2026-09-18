"""Build agentic chunks for a bounded JSONL sample using Ollama."""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.chunking.agentic import OllamaBoundaryAgent, chunk_records


def read_records(path: Path, limit: int) -> Iterator[dict[str, Any]]:
    """Read at most ``limit`` JSONL flow records."""

    with path.open("r", encoding="utf-8") as handle:
        for position, line in enumerate(handle):
            if position >= limit:
                break
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError(f"Line {position + 1} is not a JSON object")
            yield record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--model", default="qwen2.5:7b")
    parser.add_argument("--max-records", type=int, default=8)
    parser.add_argument("--max-chars", type=int, default=4096)
    parser.add_argument("--sleep-seconds", type=float, default=0.1)
    parser.add_argument("--progress-every", type=int, default=25)
    args = parser.parse_args()

    if args.limit < 1:
        parser.error("--limit must be at least 1")
    if args.max_records < 1:
        parser.error("--max-records must be at least 1")
    if args.max_chars < 1:
        parser.error("--max-chars must be at least 1")
    if args.sleep_seconds < 0:
        parser.error("--sleep-seconds cannot be negative")
    if args.progress_every < 1:
        parser.error("--progress-every must be at least 1")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    records = list(read_records(args.input, args.limit))
    agent = OllamaBoundaryAgent(model=args.model)

    decisions = 0
    chunks_written = 0
    chunks = []

    def delayed_decider(previous_text: str, current_text: str) -> bool:
        nonlocal decisions
        if decisions:
            time.sleep(args.sleep_seconds)
        decisions += 1
        if decisions % args.progress_every == 0:
            print(f"Ollama boundary decisions: {decisions}", file=sys.stderr)
        return agent(previous_text, current_text)

    with args.output.open("w", encoding="utf-8") as handle:
        for chunk in chunk_records(
            records,
            boundary_decider=delayed_decider,
            split_name="train_sample",
            max_records=args.max_records,
            max_chars=args.max_chars,
        ):
            handle.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + "\n")
            handle.flush()
            chunks.append(chunk)
            chunks_written += 1

    source_ids = {str(record["id"]) for record in records}
    chunk_ids = {
        source_id for chunk in chunks for source_id in chunk.source_flow_ids
    }
    summary = {
        "input": str(args.input),
        "output": str(args.output),
        "model": args.model,
        "input_records": len(records),
        "output_chunks": chunks_written,
        "boundary_decisions": decisions,
        "source_ids_covered": len(source_ids & chunk_ids),
        "source_ids_missing": len(source_ids - chunk_ids),
        "max_records_per_chunk": max(
            (len(chunk.source_flow_ids) for chunk in chunks), default=0
        ),
        "max_chars_observed": max(
            (len(chunk.text) for chunk in chunks), default=0
        ),
        "fallback_decisions": sum(
            int(chunk.metadata["fallback_decisions"]) for chunk in chunks
        ),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
