"""Create controlled poisoned copies of a clean JSONL knowledge base."""

from __future__ import annotations

import argparse
import copy
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any


def _read(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def build_poisoned_copy(
    clean_path: Path,
    catalog_path: Path,
    output_path: Path,
    *,
    rate: float,
    seed: int,
    attack_type: str | None = None,
) -> dict[str, Any]:
    if not 0 < rate <= 1:
        raise ValueError("rate must be greater than 0 and at most 1")
    clean_records = _read(clean_path)
    catalog = _read(catalog_path)
    if attack_type is not None:
        catalog = [item for item in catalog if item["attack_type"] == attack_type]
    if not catalog:
        raise ValueError("No attack records available after filtering")

    poison_count = max(1, round(len(clean_records) * rate))
    rng = random.Random(seed)
    selected = [catalog[index % len(catalog)] for index in range(poison_count)]
    rng.shuffle(selected)
    poisoned_records: list[dict[str, Any]] = []
    for instance, catalog_record in enumerate(selected, start=1):
        record = copy.deepcopy(catalog_record["poisoned_record"])
        record["id"] = f"{record['id']}_instance_{instance:06d}"
        metadata = dict(record.get("metadata", {}))
        metadata["poison_instance"] = instance
        metadata["poison_rate"] = rate
        record["metadata"] = metadata
        poisoned_records.append(record)

    output_records = clean_records + poisoned_records
    rng.shuffle(output_records)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for record in output_records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    return {
        "clean_input": str(clean_path),
        "catalog": str(catalog_path),
        "output": str(output_path),
        "rate": rate,
        "seed": seed,
        "clean_records": len(clean_records),
        "poisoned_records": len(poisoned_records),
        "total_records": len(output_records),
        "attack_types": dict(Counter(item["attack_type"] for item in selected)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("clean", type=Path)
    parser.add_argument("catalog", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--rate", type=float, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--attack-type", choices=["black_box", "white_box"])
    args = parser.parse_args()
    summary = build_poisoned_copy(
        args.clean,
        args.catalog,
        args.output,
        rate=args.rate,
        seed=args.seed,
        attack_type=args.attack_type,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
