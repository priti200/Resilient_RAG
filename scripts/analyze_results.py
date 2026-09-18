"""Summarize experiment JSONL results and write a report."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.evaluation.metrics import classification_metrics, latency_metrics, refusal_metrics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for path in args.inputs:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                groups[(row.get("system", "unknown"), row.get("kind", "clean"))].append(row)

    summary = {}
    for key, rows in sorted(groups.items()):
        system, kind = key
        summary[f"{system}:{kind}"] = {
            "classification": classification_metrics(rows) if kind == "clean" else {},
            "refusal": refusal_metrics(rows),
            "latency": latency_metrics(rows),
            "attack_success_rate": (
                sum(bool(row.get("attack_succeeded")) for row in rows) / len(rows)
                if kind == "attack" and rows
                else None
            ),
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
