"""Select a deterministic stratified attack subset for deadline experiments."""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--per-goal-type", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    groups = defaultdict(list)
    with args.input.open("r", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            groups[(record["goal"], record["attack_type"])].append(record)
    selected = []
    for key in sorted(groups):
        values = list(groups[key])
        stable_offset = sum(ord(char) for char in "|".join(key))
        random.Random(args.seed + stable_offset).shuffle(values)
        selected.extend(values[: args.per_goal_type])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for record in selected:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(json.dumps({"output": str(args.output), "attacks": len(selected), "groups": {str(k): len(v) for k, v in groups.items()}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
