"""Run paired descriptive/significance tests for clean system comparisons."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import ttest_rel, wilcoxon

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.evaluation.metrics import extract_label


def _read(path: Path) -> dict[str, dict]:
    with path.open("r", encoding="utf-8") as handle:
        return {row["query_id"]: row for line in handle for row in [json.loads(line)]}


def paired_summary(baseline_path: Path, resilient_path: Path) -> dict:
    baseline = _read(baseline_path)
    resilient = _read(resilient_path)
    ids = sorted(set(baseline) & set(resilient))
    baseline_correct = np.asarray(
        [extract_label(baseline[item]["answer"]) == baseline[item].get("expected_label") for item in ids],
        dtype=float,
    )
    resilient_correct = np.asarray(
        [extract_label(resilient[item]["answer"]) == resilient[item].get("expected_label") for item in ids],
        dtype=float,
    )
    baseline_latency = np.asarray(
        [sum(baseline[item].get("timings_ms", {}).values()) for item in ids], dtype=float
    )
    resilient_latency = np.asarray(
        [sum(resilient[item].get("timings_ms", {}).values()) for item in ids], dtype=float
    )
    return {
        "paired_queries": len(ids),
        "baseline_accuracy": float(baseline_correct.mean()),
        "resilient_accuracy": float(resilient_correct.mean()),
        "accuracy_difference": float(resilient_correct.mean() - baseline_correct.mean()),
        "accuracy_wilcoxon_p": float(wilcoxon(baseline_correct, resilient_correct, zero_method="zsplit").pvalue),
        "accuracy_ttest_p": float(ttest_rel(baseline_correct, resilient_correct).pvalue),
        "baseline_mean_latency_ms": float(baseline_latency.mean()),
        "resilient_mean_latency_ms": float(resilient_latency.mean()),
        "latency_wilcoxon_p": float(wilcoxon(baseline_latency, resilient_latency).pvalue),
        "latency_ttest_p": float(ttest_rel(baseline_latency, resilient_latency).pvalue),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline", type=Path)
    parser.add_argument("resilient", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = paired_summary(args.baseline, args.resilient)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
