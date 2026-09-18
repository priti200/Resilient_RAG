"""Build a deterministic proportional sample for the clean knowledge base."""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _read_records(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            record = json.loads(line)
            if not isinstance(record, dict) or "id" not in record or "text" not in record:
                raise ValueError(f"Invalid flow record at line {line_number}")
            yield record


def _label(record: dict[str, Any]) -> str:
    value = record.get("label")
    if value is None and isinstance(record.get("metadata"), dict):
        value = record["metadata"].get("CategoryLabel")
    return str(value) if value is not None else "unknown"


def _quotas(counts: Counter[str], total: int) -> dict[str, int]:
    if total < 1:
        raise ValueError("sample size must be at least 1")
    available = sum(counts.values())
    if total > available:
        raise ValueError(f"sample size {total} exceeds available records {available}")

    exact = {label: count * total / available for label, count in counts.items()}
    result = {label: min(counts[label], int(value)) for label, value in exact.items()}
    remaining = total - sum(result.values())
    order = sorted(
        counts,
        key=lambda label: (exact[label] - int(exact[label]), counts[label]),
        reverse=True,
    )
    for label in order:
        if remaining == 0:
            break
        if result[label] < counts[label]:
            result[label] += 1
            remaining -= 1
    return result


def build_sample(
    input_path: Path,
    output_path: Path,
    sample_size: int,
    seed: int,
    strategy: str = "proportional",
) -> dict[str, Any]:
    counts = Counter(_label(record) for record in _read_records(input_path))
    if strategy == "proportional":
        quotas = _quotas(counts, sample_size)
    elif strategy == "balanced":
        labels = sorted(counts)
        base, remainder = divmod(sample_size, len(labels))
        quotas = {label: base + (index < remainder) for index, label in enumerate(labels)}
        if any(quotas[label] > counts[label] for label in labels):
            raise ValueError("balanced sample size exceeds a class's available records")
    else:
        raise ValueError("strategy must be proportional or balanced")
    reservoirs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen = Counter()
    rng = random.Random(seed)

    for record in _read_records(input_path):
        label = _label(record)
        seen[label] += 1
        reservoir = reservoirs[label]
        quota = quotas[label]
        if len(reservoir) < quota:
            reservoir.append(record)
        else:
            replacement = rng.randrange(seen[label])
            if replacement < quota:
                reservoir[replacement] = record

    selected = [record for label in sorted(reservoirs) for record in reservoirs[label]]
    rng.shuffle(selected)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for record in selected:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    selected_counts = Counter(_label(record) for record in selected)
    return {
        "input": str(input_path),
        "output": str(output_path),
        "seed": seed,
        "strategy": strategy,
        "requested_records": sample_size,
        "written_records": len(selected),
        "source_counts": dict(sorted(counts.items())),
        "quotas": dict(sorted(quotas.items())),
        "selected_counts": dict(sorted(selected_counts.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--sample-size", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--strategy", choices=["proportional", "balanced"], default="proportional")
    args = parser.parse_args()
    summary = build_sample(args.input, args.output, args.sample_size, args.seed, args.strategy)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
