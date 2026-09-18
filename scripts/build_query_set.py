"""Build a reproducible stratified clean evaluation query set."""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path


def _label(record: dict) -> str:
    return str(record.get("label") or record.get("metadata", {}).get("CategoryLabel", "unknown"))


def build_query_set(input_path: Path, output_path: Path, *, per_class: int, seed: int) -> dict:
    reservoirs: dict[str, list[dict]] = defaultdict(list)
    seen: dict[str, int] = defaultdict(int)
    rng = random.Random(seed)
    for line_number, line in enumerate(input_path.open("r", encoding="utf-8")):
        record = json.loads(line)
        label = _label(record)
        seen[label] += 1
        reservoir = reservoirs[label]
        if len(reservoir) < per_class:
            reservoir.append(record)
        else:
            position = rng.randrange(seen[label])
            if position < per_class:
                reservoir[position] = record

    queries = []
    for label in sorted(reservoirs):
        for index, record in enumerate(reservoirs[label], start=1):
            queries.append(
                {
                    "query_id": f"clean_{label}_{index:04d}",
                    "kind": "clean",
                    "source_flow_id": record["id"],
                    "expected_label": label,
                    "query": "Classify this network flow and state whether a security alert is required.\n\n" + record["text"],
                }
            )
    rng.shuffle(queries)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for query in queries:
            handle.write(json.dumps(query, ensure_ascii=False) + "\n")
    return {"input": str(input_path), "output": str(output_path), "queries": len(queries), "per_class": per_class, "seed": seed}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--per-class", type=int, default=25)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    print(json.dumps(build_query_set(args.input, args.output, per_class=args.per_class, seed=args.seed), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
