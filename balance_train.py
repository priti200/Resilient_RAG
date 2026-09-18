import os
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
TRAIN_PATH = BASE_DIR / "data" / "cleaned" / "train.csv"
VAL_PATH = BASE_DIR / "data" / "cleaned" / "validation.csv"
TEST_PATH = BASE_DIR / "data" / "cleaned" / "test.csv"
BALANCED_TRAIN_PATH = BASE_DIR / "data" / "cleaned" / "train_balanced.csv"
REPORT_PATH = BASE_DIR / "analysis_results" / "balancing_report.txt"


def make_distribution(series):
    counts = series.value_counts(dropna=False).sort_index()
    total = int(counts.sum())
    percentages = ((counts / total) * 100.0).round(4)
    return counts.to_dict(), percentages.to_dict(), total


def main():
    train_df = pd.read_csv(TRAIN_PATH, low_memory=False)
    val_df = pd.read_csv(VAL_PATH, low_memory=False)
    test_df = pd.read_csv(TEST_PATH, low_memory=False)

    before_counts, before_pct, before_total = make_distribution(train_df["CategoryLabel"])
    target_count = min(before_counts.values()) if before_counts else 0

    if target_count <= 0:
        raise ValueError("No class counts available to balance.")

    frames = []
    for cls, count in before_counts.items():
        class_df = train_df[train_df["CategoryLabel"] == cls].copy()
        subset = class_df.sample(n=min(count, target_count), random_state=42, replace=False)
        frames.append(subset)

    balanced_df = pd.concat(frames, ignore_index=True)
    balanced_df = balanced_df.sample(frac=1.0, random_state=42).reset_index(drop=True)
    balanced_df.to_csv(BALANCED_TRAIN_PATH, index=False)

    final_counts, final_pct, final_total = make_distribution(balanced_df["CategoryLabel"])
    balanced_equal = len(set(final_counts.values())) <= 1
    status = "READY" if balanced_equal else "FAILED"

    val_counts, val_pct, val_total = make_distribution(val_df["CategoryLabel"])
    test_counts, test_pct, test_total = make_distribution(test_df["CategoryLabel"])

    lines = []
    lines.append("GE-NIS TRAIN BALANCING REPORT")
    lines.append("===========================")
    lines.append("")
    lines.append(f"Source training dataset: {TRAIN_PATH}")
    lines.append(f"Original training row count: {before_total}")
    lines.append("Original class counts:")
    for cls in sorted(before_counts):
        lines.append(f"- {cls}: {before_counts[cls]}")
    lines.append("Original class percentages:")
    for cls in sorted(before_pct):
        lines.append(f"- {cls}: {before_pct[cls]:.4f}%")
    lines.append("")
    lines.append("Balancing method: random undersampling applied to every class to the largest safe no-duplication target count")
    lines.append("Random seed: 42")
    lines.append(f"Target count per class: {target_count}")
    lines.append("Constraint: no duplication and no synthetic records were allowed; therefore the balancing target is the smallest observed class count, which is the largest safe count that preserves equal-class balancing without oversampling.")
    lines.append("")
    lines.append("Final balanced class counts:")
    for cls in sorted(final_counts):
        lines.append(f"- {cls}: {final_counts[cls]}")
    lines.append("Final class percentages:")
    for cls in sorted(final_pct):
        lines.append(f"- {cls}: {final_pct[cls]:.4f}%")
    lines.append(f"Final balanced training row count: {final_total}")
    lines.append("")
    lines.append(f"Validation row count: {val_total}")
    lines.append("Validation class distribution:")
    for cls in sorted(val_counts):
        lines.append(f"- {cls}: {val_counts[cls]}")
    lines.append("")
    lines.append(f"Test row count: {test_total}")
    lines.append("Test class distribution:")
    for cls in sorted(test_counts):
        lines.append(f"- {cls}: {test_counts[cls]}")
    lines.append("")
    lines.append(f"BALANCING STATUS: {status}")
    lines.append("")
    lines.append("Before vs after class counts:")
    all_classes = sorted(set(before_counts) | set(final_counts))
    for cls in all_classes:
        before_val = before_counts.get(cls, 0)
        after_val = final_counts.get(cls, 0)
        lines.append(f"- {cls}: {before_val} -> {after_val}")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print("Original train rows:", before_total)
    print("Original class counts:", before_counts)
    print("Target count per class:", target_count)
    print("Final balanced rows:", final_total)
    print("Final counts:", final_counts)
    print("Equal counts:", balanced_equal)
    print("Validation rows:", val_total)
    print("Test rows:", test_total)
    print("Balanced output:", BALANCED_TRAIN_PATH)
    print("Report output:", REPORT_PATH)


if __name__ == "__main__":
    main()
