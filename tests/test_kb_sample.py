"""Tests for deterministic knowledge-base sampling."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_kb_sample import build_sample


def test_proportional_sample_is_deterministic(tmp_path: Path) -> None:
    source = tmp_path / "input.jsonl"
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    records = [
        {"id": f"flow-{index}", "text": f"flow {index}", "label": label}
        for index, label in enumerate(["dos"] * 6 + ["benign"] * 3 + ["recon"])
    ]
    source.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")

    first_summary = build_sample(source, first, sample_size=5, seed=42)
    second_summary = build_sample(source, second, sample_size=5, seed=42)

    assert first_summary["selected_counts"] == second_summary["selected_counts"]
    assert first_summary["quotas"] == second_summary["quotas"]
    assert first.read_bytes() == second.read_bytes()
    assert first_summary["written_records"] == 5
    assert sum(first_summary["selected_counts"].values()) == 5


def test_balanced_sample_uses_equal_class_quotas(tmp_path: Path) -> None:
    source = tmp_path / "input.jsonl"
    output = tmp_path / "balanced.jsonl"
    records = [
        {"id": f"flow-{index}", "text": f"flow {index}", "label": label}
        for index, label in enumerate(["dos"] * 6 + ["benign"] * 3 + ["recon"])
    ]
    source.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")

    summary = build_sample(source, output, sample_size=3, seed=42, strategy="balanced")

    assert summary["quotas"] == {"benign": 1, "dos": 1, "recon": 1}
    assert summary["selected_counts"] == summary["quotas"]
