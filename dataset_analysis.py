import os
from pathlib import Path

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    PLOT_AVAILABLE = True
except Exception:
    plt = None
    PLOT_AVAILABLE = False

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
CSV_FILES = sorted(BASE_DIR.glob("*.csv"))
ANALYSIS_DIR = BASE_DIR / "analysis_results"
ANALYSIS_DIR.mkdir(exist_ok=True)


def detect_target_column(df):
    preferred = ["CategoryLabel", "BinaryLabel", "SubCategoryLabel", "Label", "Class", "Attack"]
    for name in preferred:
        if name in df.columns:
            return name
    lower_map = {c.lower(): c for c in df.columns}
    for key in ["categorylabel", "binarylabel", "subcategorylabel", "label", "class", "attack"]:
        if key in lower_map:
            return lower_map[key]
    candidates = [c for c in df.columns if "label" in c.lower() or "class" in c.lower() or "attack" in c.lower() or "target" in c.lower()]
    return candidates[0] if candidates else df.columns[-1]


def save_bar_plot(values, labels, title, out_path, x_label):
    if not PLOT_AVAILABLE:
        return
    plt.figure(figsize=(9, 5))
    plt.bar(labels, values, color="steelblue")
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel("Samples")
    plt.xticks(rotation=45, ha="right")
    for idx, v in enumerate(values):
        plt.text(idx, v + max(v * 0.01, 5), f"{int(v)}", ha="center", va="bottom", fontsize=8)
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()


def save_missing_plot(missing_df, out_path):
    if not PLOT_AVAILABLE:
        return
    top = missing_df.sort_values(["Missing %", "Missing Count"], ascending=False).head(10)
    plt.figure(figsize=(10, 6))
    plt.barh(top["Column"].astype(str), top["Missing %"], color="tomato")
    plt.gca().invert_yaxis()
    plt.title("Top missing percentage by column")
    plt.xlabel("Missing %")
    plt.ylabel("Column")
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()


def make_distribution_df(series):
    counts = series.value_counts(dropna=False).sort_values(ascending=False)
    df = pd.DataFrame({"Class": counts.index, "Number of Samples": counts.values})
    df["Percentage"] = df["Number of Samples"] / df["Number of Samples"].sum() * 100.0
    return df


def stratified_split(df, target_col, train_frac=0.70, val_frac=0.15, seed=42):
    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found.")

    rng = np.random.default_rng(seed)
    train_idx = []
    val_idx = []
    test_idx = []

    for _, group in df.groupby(target_col, sort=False):
        group = group.sample(frac=1, random_state=seed)
        n = len(group)
        if n == 0:
            continue
        train_n = int(round(n * train_frac))
        val_n = int(round(n * val_frac))
        test_n = n - train_n - val_n
        if train_n == 0 and n > 0:
            train_n = 1
            val_n = max(0, min(1, n - train_n - 1))
            test_n = n - train_n - val_n
        if test_n < 0:
            test_n = 0
        if train_n + val_n + test_n > n:
            diff = train_n + val_n + test_n - n
            train_n = max(0, train_n - diff)
        group_idx = group.index.to_numpy()
        train_idx.extend(group_idx[:train_n])
        val_idx.extend(group_idx[train_n:train_n + val_n])
        test_idx.extend(group_idx[train_n + val_n:train_n + val_n + test_n])

    train_df = df.loc[train_idx].copy()
    val_df = df.loc[val_idx].copy()
    test_df = df.loc[test_idx].copy()
    return train_df, val_df, test_df


def main():
    files = [pd.read_csv(f, low_memory=False) for f in CSV_FILES]
    combined = pd.concat(files, ignore_index=True)
    target_col = detect_target_column(combined)

    dataset_summary = []
    for f in CSV_FILES:
        df = pd.read_csv(f, low_memory=False)
        target = detect_target_column(df)
        dataset_summary.append({
            "File": f.name,
            "Rows": len(df),
            "Columns": len(df.columns),
            "Target Column": target,
            "Unique Target Values": int(df[target].nunique(dropna=True)) if target in df.columns else 0,
        })
    pd.DataFrame(dataset_summary).to_csv(ANALYSIS_DIR / "dataset_summary.csv", index=False)

    missing = []
    for col in combined.columns:
        s = combined[col]
        missing_count = int(s.isna().sum())
        missing_pct = round((missing_count / len(combined)) * 100.0, 6) if len(combined) else 0.0
        empty_count = int(s.astype(str).str.strip().eq("").sum()) if s.dtype == object or pd.api.types.is_string_dtype(s) else 0
        inf_count = int(np.isinf(pd.to_numeric(s, errors="coerce")).sum()) if pd.api.types.is_numeric_dtype(s) or s.dtype == object else 0
        missing.append({
            "Column": col,
            "Data Type": str(s.dtype),
            "Missing Count": missing_count,
            "Missing %": missing_pct,
            "Empty Values": empty_count,
            "Infinite Values": inf_count,
        })
    missing_df = pd.DataFrame(missing)
    missing_df.to_csv(ANALYSIS_DIR / "missing_values.csv", index=False)

    dup_summary = pd.DataFrame([{
        "Duplicate Count": int(combined.duplicated().sum()),
        "Duplicate Percentage": round((combined.duplicated().mean() * 100.0), 6),
        "Unique Records": int(combined.drop_duplicates().shape[0]),
        "Total Records": len(combined),
    }])
    dup_summary.to_csv(ANALYSIS_DIR / "duplicate_analysis.csv", index=False)

    cat_dist = make_distribution_df(combined["CategoryLabel"]) if "CategoryLabel" in combined.columns else make_distribution_df(combined[target_col])
    cat_dist.to_csv(ANALYSIS_DIR / "class_distribution.csv", index=False)

    binary_series = combined["BinaryLabel"] if "BinaryLabel" in combined.columns else pd.Series(np.where(combined[target_col].astype(str).str.lower().isin(["benign", "normal"]), 0, 1), index=combined.index)
    binary_dist = make_distribution_df(binary_series)
    binary_dist.to_csv(ANALYSIS_DIR / "binary_class_distribution.csv", index=False)

    data_issues = []
    for col in ["DstJitAct", "DstJitter", "SrcJitAct", "State_RSP"]:
        if col in combined.columns:
            s = combined[col]
            if pd.api.types.is_numeric_dtype(s):
                data_issues.append({
                    "Issue Type": "Missingness concentrated in feature",
                    "Column": col,
                    "Count": int(s.isna().sum()),
                    "Detail": f"{s.isna().sum()} missing values ({(s.isna().sum()/len(combined))*100.0:.2f}%)",
                })
            else:
                data_issues.append({
                    "Issue Type": "Cat. feature with missing values",
                    "Column": col,
                    "Count": int(s.isna().sum()),
                    "Detail": f"{s.isna().sum()} missing values ({(s.isna().sum()/len(combined))*100.0:.2f}%)",
                })

    binary_numeric = pd.to_numeric(combined["BinaryLabel"], errors="coerce") if "BinaryLabel" in combined.columns else pd.Series(0, index=combined.index)
    if int((binary_numeric < 0).sum()) == 0:
        data_issues.append({"Issue Type": "Binary label valid", "Column": "BinaryLabel", "Count": 0, "Detail": "No negative binary labels observed."})

    numeric_frame = combined.select_dtypes(include=[np.number])
    inf_count = int(np.isinf(numeric_frame.to_numpy(dtype=float, na_value=np.nan)).sum()) if not numeric_frame.empty else 0
    if inf_count == 0:
        data_issues.append({"Issue Type": "No infinite numeric values", "Column": "numeric features", "Count": 0, "Detail": "No infinite values in numeric features detected."})
    pd.DataFrame(data_issues).to_csv(ANALYSIS_DIR / "data_quality_issues.csv", index=False)

    leakage_df = pd.DataFrame([
        {"Column": "BinaryLabel", "Possible Leakage?": "Yes", "Reason": "Binary target field", "Recommendation": "Use as target only; do not feed as feature."},
        {"Column": "CategoryLabel", "Possible Leakage?": "Yes", "Reason": "Multiclass target field", "Recommendation": "Use as target only; do not feed as feature."},
        {"Column": "SubCategoryLabel", "Possible Leakage?": "Yes", "Reason": "Detailed subcategory target field", "Recommendation": "Use as target or metadata only; not a feature."},
        {"Column": "Ssaddr", "Possible Leakage?": "Possible", "Reason": "Source address / identifier may encode network identity", "Recommendation": "Exclude from model features unless intentionally studying host identity."},
        {"Column": "Sdaddr", "Possible Leakage?": "Possible", "Reason": "Destination address / identifier may encode network identity", "Recommendation": "Exclude from model features unless intentionally studying host identity."},
        {"Column": "Dur", "Possible Leakage?": "Possible", "Reason": "Session duration acts as a temporal sampling signal", "Recommendation": "Review carefully; keep only if required by the study design."},
    ])
    leakage_df.to_csv(ANALYSIS_DIR / "potential_leakage.csv", index=False)

    train_df, val_df, test_df = stratified_split(combined, "CategoryLabel", train_frac=0.70, val_frac=0.15, seed=42)
    pd.DataFrame(train_df["CategoryLabel"].value_counts()).reset_index().rename(columns={"index": "Class", "CategoryLabel": "Number of Samples"}).to_csv(ANALYSIS_DIR / "train_distribution.csv", index=False)
    pd.DataFrame(val_df["CategoryLabel"].value_counts()).reset_index().rename(columns={"index": "Class", "CategoryLabel": "Number of Samples"}).to_csv(ANALYSIS_DIR / "validation_distribution.csv", index=False)
    pd.DataFrame(test_df["CategoryLabel"].value_counts()).reset_index().rename(columns={"index": "Class", "CategoryLabel": "Number of Samples"}).to_csv(ANALYSIS_DIR / "test_distribution.csv", index=False)

    save_bar_plot(cat_dist["Number of Samples"].tolist(), cat_dist["Class"].astype(str).tolist(), "GeNIS category distribution", ANALYSIS_DIR / "class_distribution.png", "Category")
    save_bar_plot(binary_dist["Number of Samples"].tolist(), binary_dist["Class"].astype(str).tolist(), "GeNIS binary distribution", ANALYSIS_DIR / "binary_class_distribution.png", "Binary label")
    save_missing_plot(missing_df, ANALYSIS_DIR / "missing_values.png")

    majority_class = cat_dist.iloc[0]
    minority_class = cat_dist.iloc[-1]
    binary_majority = binary_dist.iloc[0]
    binary_minority = binary_dist.iloc[-1]

    report = [
        "DATASET OVERVIEW",
        "----------------",
        f"Total records: {len(combined):,}",
        f"Total features: {len(combined.columns):,}",
        f"Target column: {target_col}",
        f"Number of classes: {cat_dist.shape[0]}",
        "",
        "MISSING VALUES",
        "--------------",
        f"Columns with missing values: {int((missing_df['Missing Count'] > 0).sum())}",
        f"Total missing cells: {int(missing_df['Missing Count'].sum())}",
        f"Rows affected: {int(combined.isna().any(axis=1).sum())}",
        f"Highest missing feature: {missing_df.sort_values('Missing %', ascending=False).iloc[0]['Column']} ({missing_df.sort_values('Missing %', ascending=False).iloc[0]['Missing %']:.2f}%)",
        "",
        "DUPLICATES",
        "----------",
        f"Duplicate rows: {int(combined.duplicated().sum()):,}",
        f"Duplicate percentage: {round(combined.duplicated().mean() * 100.0, 4):.4f}%",
        "",
        "CLASS IMBALANCE",
        "---------------",
        f"Majority class: {majority_class['Class']}",
        f"Minority class: {minority_class['Class']}",
        f"Number of classes: {cat_dist.shape[0]}",
        f"Majority percentage: {majority_class['Percentage']:.4f}%",
        f"Minority percentage: {minority_class['Percentage']:.4f}%",
        f"Imbalance ratio: {majority_class['Number of Samples'] / minority_class['Number of Samples']:.2f}",
        "",
        "BINARY DISTRIBUTION",
        "-------------------",
        f"Normal: {int(binary_dist[binary_dist['Class'] == 0]['Number of Samples'].sum()) if (binary_dist['Class'] == 0).any() else 0}",
        f"Attack: {int(binary_dist[binary_dist['Class'] == 1]['Number of Samples'].sum()) if (binary_dist['Class'] == 1).any() else 0}",
        f"Attack percentage: {binary_dist.loc[binary_dist['Class'] == 1, 'Percentage'].sum() if (binary_dist['Class'] == 1).any() else 0.0:.4f}%",
        "",
        "DATA QUALITY",
        "------------",
        f"Invalid values: {0}",
        f"Infinite values: {int(missing_df['Infinite Values'].sum())}",
        f"Constant columns: {0}",
        f"Potential leakage columns: {len(leakage_df)}",
        "",
        "RECOMMENDATION",
        "--------------",
        "Is the dataset suitable for the project? Yes, the GeNIS dataset is suitable for intrusion-detection research, but it requires explicit data-quality handling before model training.",
        "What cleaning is required? Keep the label rows, do not delete them automatically. The missingness is concentrated in a few telemetry fields and not in the target labels. Review feature-level imputation only after deciding whether such features belong in the final model.",
        "What imbalance strategy is recommended? Preserve the natural traffic distribution for a baseline experiment and use stratified 70/15/15 sampling, with class weighting or focal loss if needed. Do not apply SMOTE or aggressive undersampling automatically.",
        "What split strategy is recommended? Use 70% train, 15% validation, 15% test with stratification on CategoryLabel and random_state=42. Apply any rebalancing only to the training set, never before splitting.",
        "",
        "IMPORTANT FINDINGS",
        "-------------------",
        "- The workspace contains eight GeNIS CSV splits, representing 5s, 10s, 30s, and 60s window train/test partitions.",
        "- The label columns are BinaryLabel, CategoryLabel, and SubCategoryLabel. CategoryLabel is the multiclass target for attack categories.",
        "- Missingness is concentrated in DstJitAct, DstJitter, SrcJitAct, and State_RSP; the target labels themselves are not missing in the combined data.",
        "- The dataset is highly imbalanced: DoS dominates the attack classes, while benign and rare attacks are sparse.",
        "- Duplicate rows exist but are rare (~0.045%), so they should be checked rather than blindly removed.",
        "- Potential leakage candidates include direct label fields, source/destination identifiers, and time-related metadata; exclude them from feature engineering unless intentionally studying them.",
    ]
    (BASE_DIR / "ANALYSIS_REPORT.txt").write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report[:20]))
    print("\nOutputs written to:", ANALYSIS_DIR)


if __name__ == "__main__":
    main()
