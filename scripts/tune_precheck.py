"""Tune pre-check thresholds against clean and synthetic attack samples."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.defense.precheck import check_text


def _read(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("clean", type=Path)
    parser.add_argument("attacks", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--clean-limit", type=int, default=1000)
    args = parser.parse_args()
    clean = _read(args.clean)[: args.clean_limit]
    attacks = _read(args.attacks)
    clean_results = [check_text(row["text"]) for row in clean]
    attack_results = [check_text(row["poisoned_record"]["text"]) for row in attacks]
    clean_rejection_rate = sum(not result.accepted for result in clean_results) / len(clean_results)
    attack_detection_rate = sum(not result.accepted for result in attack_results) / len(attack_results)
    if clean_rejection_rate > 0.01:
        raise RuntimeError(f"Clean rejection rate {clean_rejection_rate:.4f} exceeds 1% target")

    config = {
        "max_language_score": 0.0,
        "max_perplexity": None,
        "clean_rejection_rate": clean_rejection_rate,
        "attack_detection_rate": attack_detection_rate,
        "clean_samples": len(clean),
        "attack_samples": len(attacks),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    print(json.dumps(config, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
