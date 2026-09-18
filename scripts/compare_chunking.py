"""Compare chunk isolation on a bounded JSONL sample."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.chunking.fixed_size import DEFAULT_MAX_CHARS
from src.chunking.fixed_size import chunk_records as fixed_chunks
from src.chunking.semantic import chunk_records as semantic_chunks


def _records(path: Path, limit: int) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for position, line in enumerate(handle):
            if position >= limit:
                break
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError(f"Line {position + 1} is not a JSON object")
            yield record


def _summary(chunks: list[Any]) -> dict[str, float | int]:
    counts = [len(chunk.source_flow_ids) for chunk in chunks]
    return {
        "chunks": len(chunks),
        "multi_flow_chunks": sum(count > 1 for count in counts),
        "max_flows_per_chunk": max(counts, default=0),
        "mean_flows_per_chunk": round(sum(counts) / len(counts), 3) if counts else 0.0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    args = parser.parse_args()

    if args.limit < 1:
        parser.error("--limit must be at least 1")

    records = list(_records(args.input, args.limit))
    semantic = list(semantic_chunks(records, split_name="sample"))
    fixed = list(fixed_chunks(records, split_name="sample", max_chars=args.max_chars))
    print(json.dumps({"input_records": len(records), "semantic": _summary(semantic), "fixed": _summary(fixed)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
