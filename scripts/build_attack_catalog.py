"""Build a deterministic synthetic attack catalog."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.attacks.black_box import generate_candidates
from src.attacks.templates import ATTACK_GOALS, build_target_query, poison_record
from src.attacks.white_box import rank_candidates
from src.index.embedder import TextEmbedder


def records(path: Path, limit: int):
    with path.open("r", encoding="utf-8") as handle:
        for position, line in enumerate(handle):
            if position >= limit:
                break
            yield json.loads(line)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--targets", type=int, default=20)
    parser.add_argument("--variants", type=int, default=4)
    parser.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    args = parser.parse_args()
    if args.targets < 1 or args.variants < 1:
        parser.error("targets and variants must be positive")

    target_query = build_target_query()
    target_records = list(records(args.input, args.targets))
    embedder = TextEmbedder(args.model)
    output_records: list[dict[str, Any]] = []
    attack_number = 0

    for target_record in target_records:
        for goal in ATTACK_GOALS:
            candidates = generate_candidates(
                target_record,
                goal=goal,
                target_query=target_query,
                limit=args.variants,
            )
            ranked_candidates = rank_candidates(target_query, candidates, embedder=embedder)
            for candidate in candidates + ranked_candidates:
                attack_number += 1
                attack_id = f"attack_{attack_number:05d}"
                poisoned = poison_record(
                    target_record,
                    attack_id=attack_id,
                    goal=goal,
                    instruction=candidate["instruction"],
                    attack_type=candidate["attack_type"],
                    target_query=target_query,
                )
                output_records.append(
                    {
                        "attack_id": attack_id,
                        "attack_type": candidate["attack_type"],
                        "goal": goal,
                        "target_query": target_query,
                        "source_record_id": target_record["id"],
                        "instruction": candidate["instruction"],
                        "retrieval_similarity": candidate.get("retrieval_similarity"),
                        "poisoned_record": poisoned,
                    }
                )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for record in output_records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(json.dumps({"output": str(args.output), "attacks": len(output_records)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
