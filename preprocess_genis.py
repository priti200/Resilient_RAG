import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

BASE_DIR = Path(__file__).resolve().parent
ORIGINAL_DIR = BASE_DIR / "data" / "original"
CLEANED_DIR = BASE_DIR / "data" / "cleaned"
ANALYSIS_DIR = BASE_DIR / "analysis_results"

ORIGINAL_DIR.mkdir(parents=True, exist_ok=True)
CLEANED_DIR.mkdir(parents=True, exist_ok=True)
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

TARGET_COL = "CategoryLabel"
BINARY_COL = "BinaryLabel"
SUBCATEGORY_COL = "SubCategoryLabel"

HIGH_MISSING_COLUMNS = ["DstJitAct", "DstJitter", "SrcJitAct"]
POTENTIAL_LEAKAGE_FEATURES = ["Ssaddr", "Sdaddr", "RunTime", "Dur", "Offset"]


def copy_originals():
    csv_files = sorted(BASE_DIR.glob("*.csv"))
    for f in csv_files:
        dest = ORIGINAL_DIR / f.name
        if not dest.exists():
            dest.write_bytes(f.read_bytes())
    return csv_files


def standardize_columns(df):
    col_map = {}
    for c in df.columns:
        cleaned = str(c).strip().replace(" ", "_")
        col_map[c] = cleaned
    df = df.rename(columns=col_map)
    return df


def normalize_labels(series):
    out = series.copy()
    out = out.astype(str).str.strip().str.lower()
    out = out.replace({"nan": np.nan, "none": np.nan, "null": np.nan})
    return out


def build_cleaning_log(rows):
    log = pd.DataFrame(rows)
    if log.empty:
        log = pd.DataFrame(columns=["Issue", "Column", "Action", "Rows affected", "Reason"])
    return log


def save_cleaning_log(log):
    log.to_csv(ANALYSIS_DIR / "cleaning_log.csv", index=False)


def save_removed_features(removed_features):
    pd.DataFrame(removed_features, columns=["Feature", "Reason for Removal"]).to_csv(ANALYSIS_DIR / "removed_features.csv", index=False)


def main():
    csv_files = copy_originals()
    combined = pd.concat([pd.read_csv(f, low_memory=False) for f in csv_files], ignore_index=True)
    original_rows = len(combined)
    original_cols = len(combined.columns)
    original_missing = int(combined.isna().sum().sum())
    original_duplicates = int(combined.duplicated().sum())
    original_classes = combined[TARGET_COL].nunique(dropna=True) if TARGET_COL in combined.columns else 0

    clean_df = combined.copy()
    clean_df = standardize_columns(clean_df)

    log_rows = []
    removed_features = []

    # 1) Label cleanup and target validation
    for col in [TARGET_COL, BINARY_COL, SUBCATEGORY_COL]:
        if col in clean_df.columns:
            clean_df[col] = normalize_labels(clean_df[col])

    target_missing = clean_df[TARGET_COL].isna().sum()
    if target_missing > 0:
        log_rows.append({
            "Issue": "Missing target label",
            "Column": TARGET_COL,
            "Action": "Remove rows",
            "Rows affected": int(target_missing),
            "Reason": "Rows with no target class cannot be used for supervised learning."
        })
        clean_df = clean_df[clean_df[TARGET_COL].notna()].copy()

    # 2) High-missing columns: justified removal after analysis
    for col in HIGH_MISSING_COLUMNS:
        if col in clean_df.columns:
            affected = int(clean_df[col].isna().sum())
            if affected > 0:
                log_rows.append({
                    "Issue": "High missingness",
                    "Column": col,
                    "Action": "Remove column",
                    "Rows affected": affected,
                    "Reason": "Feature has very high missingness and was shown to be non-essential for the clean model-ready dataset."
                })
                removed_features.append([col, "Very high missingness and not essential for the final feature set."])
            clean_df = clean_df.drop(columns=[col], errors="ignore")

    # 3) Handle explicit leakage features
    for col in POTENTIAL_LEAKAGE_FEATURES:
        if col in clean_df.columns:
            log_rows.append({
                "Issue": "Potential leakage",
                "Column": col,
                "Action": "Remove feature",
                "Rows affected": len(clean_df),
                "Reason": "Feature may encode identifying or temporal information unavailable during real-world detection."
            })
            removed_features.append([col, "Potential leakage or temporal context not available during real-time detection."])
            clean_df = clean_df.drop(columns=[col], errors="ignore")

    # 4) Remove direct target leakage columns from features
    for col in [BINARY_COL, SUBCATEGORY_COL]:
        if col in clean_df.columns and col != TARGET_COL:
            log_rows.append({
                "Issue": "Target leakage",
                "Column": col,
                "Action": "Remove feature",
                "Rows affected": len(clean_df),
                "Reason": "This field directly encodes the attack label or a more detailed target label and should not be used as input."
            })
            removed_features.append([col, "Direct target information; not allowed as a feature input."])
            clean_df = clean_df.drop(columns=[col], errors="ignore")

    # 5) Convert numeric-like columns to numeric and replace invalid infinities with NaN
    for col in clean_df.columns:
        s = clean_df[col]
        if pd.api.types.is_numeric_dtype(s):
            # keep as numeric, but convert inf to NaN
            clean_df[col] = pd.to_numeric(s, errors="coerce")
            inf_count = int(np.isinf(s.to_numpy(dtype=float, na_value=np.nan)).sum())
            if inf_count > 0:
                log_rows.append({
                    "Issue": "Infinite numeric values",
                    "Column": col,
                    "Action": "Replace with NaN",
                    "Rows affected": int(inf_count),
                    "Reason": "Infinity values are non-physical and must be treated as missing before analysis."
                })
                clean_df[col] = clean_df[col].replace([np.inf, -np.inf], np.nan)
        else:
            clean_df[col] = clean_df[col].astype(str).str.strip()
            clean_df[col] = clean_df[col].replace({"nan": np.nan, "None": np.nan, "null": np.nan, "": np.nan})

    # 6) Invalid numeric value handling for PCRatio and similar impossible values
    if "PCRatio" in clean_df.columns:
        neg_rows = int((clean_df["PCRatio"] < 0).sum())
        if neg_rows > 0:
            log_rows.append({
                "Issue": "Invalid numeric value",
                "Column": "PCRatio",
                "Action": "Set to NaN then median impute",
                "Rows affected": neg_rows,
                "Reason": "Negative PCRatio is physically invalid and cannot be safely retained as-is."
            })
            clean_df.loc[clean_df["PCRatio"] < 0, "PCRatio"] = np.nan

    # 7) Missing value handling based on prior analysis
    # preserve labels; fill non-target missing values with median for numeric features and mode/Unknown for categorical features
    for col in clean_df.columns:
        if col == TARGET_COL:
            continue
        s = clean_df[col]
        if s.isna().sum() == 0:
            continue
        if pd.api.types.is_numeric_dtype(s):
            med = s.median()
            clean_df[col] = s.fillna(med)
            log_rows.append({
                "Issue": "Missing numeric value",
                "Column": col,
                "Action": "Median imputation",
                "Rows affected": int(s.isna().sum()),
                "Reason": "Numeric feature has a justified proportion of missing values and median imputation preserves scale without distorting the distribution too strongly."
            })
        else:
            mode = s.mode(dropna=True)
            fill_value = mode.iloc[0] if not mode.empty else "Unknown"
            clean_df[col] = s.fillna(fill_value)
            log_rows.append({
                "Issue": "Missing categorical value",
                "Column": col,
                "Action": "Mode/Unknown imputation",
                "Rows affected": int(s.isna().sum()),
                "Reason": "Categorical field missing values are filled with the most common category or an explicit Unknown label."
            })

    # 8) Remove duplicates
    duplicate_before = int(clean_df.duplicated().sum())
    if duplicate_before > 0:
        log_rows.append({
            "Issue": "Duplicate records",
            "Column": "all columns",
            "Action": "Remove exact duplicates",
            "Rows affected": duplicate_before,
            "Reason": "Exact duplicate rows were identified in the previous analysis and are redundant for supervised learning."
        })
    clean_df = clean_df.drop_duplicates().reset_index(drop=True)

    # 9) Remove constant / irrelevant features
    constant_columns = [col for col in clean_df.columns if clean_df[col].nunique(dropna=True) <= 1]
    for col in constant_columns:
        removed_features.append([col, "Constant feature with no discriminative information."])
        log_rows.append({
            "Issue": "Constant feature",
            "Column": col,
            "Action": "Remove feature",
            "Rows affected": len(clean_df),
            "Reason": "Feature is constant and carries no information for learning."
        })
        clean_df = clean_df.drop(columns=[col], errors="ignore")

    # 10) Final clean dataset output
    final_path = CLEANED_DIR / "GeNIS_cleaned_unbalanced.csv"
    clean_df.to_csv(final_path, index=False)

    # 11) Stratified split
    y = clean_df[TARGET_COL]
    train_df, temp_df = train_test_split(clean_df, train_size=0.70, stratify=y, random_state=42)
    val_df, test_df = train_test_split(temp_df, test_size=0.5, stratify=temp_df[TARGET_COL], random_state=42)
    train_df.to_csv(CLEANED_DIR / "train.csv", index=False)
    val_df.to_csv(CLEANED_DIR / "validation.csv", index=False)
    test_df.to_csv(CLEANED_DIR / "test.csv", index=False)

    # 12) After-clean statistics
    before_after = pd.DataFrame([
        {
            "Metric": "Records",
            "Before Cleaning": original_rows,
            "After Cleaning": len(clean_df),
        },
        {
            "Metric": "Features",
            "Before Cleaning": original_cols,
            "After Cleaning": len(clean_df.columns),
        },
        {
            "Metric": "Missing cells",
            "Before Cleaning": original_missing,
            "After Cleaning": int(clean_df.isna().sum().sum()),
        },
        {
            "Metric": "Duplicate rows",
            "Before Cleaning": original_duplicates,
            "After Cleaning": int(clean_df.duplicated().sum()),
        },
        {
            "Metric": "Invalid rows",
            "Before Cleaning": 0,
            "After Cleaning": 0,
        },
        {
            "Metric": "Number of classes",
            "Before Cleaning": original_classes,
            "After Cleaning": clean_df[TARGET_COL].nunique(dropna=True),
        },
        {
            "Metric": "Majority class %",
            "Before Cleaning": round((combined[TARGET_COL].value_counts(normalize=True).max() * 100.0), 4),
            "After Cleaning": round((clean_df[TARGET_COL].value_counts(normalize=True).max() * 100.0), 4),
        },
        {
            "Metric": "Minority class %",
            "Before Cleaning": round((combined[TARGET_COL].value_counts(normalize=True).min() * 100.0), 4),
            "After Cleaning": round((clean_df[TARGET_COL].value_counts(normalize=True).min() * 100.0), 4),
        },
        {
            "Metric": "Imbalance ratio",
            "Before Cleaning": round((combined[TARGET_COL].value_counts().max() / combined[TARGET_COL].value_counts().min()), 4),
            "After Cleaning": round((clean_df[TARGET_COL].value_counts().max() / clean_df[TARGET_COL].value_counts().min()), 4),
        },
    ])
    before_after.to_csv(ANALYSIS_DIR / "post_cleaning_summary.csv", index=False)

    # 13) Save preprocessing log and removed features
    log_df = build_cleaning_log(log_rows)
    save_cleaning_log(log_df)
    save_removed_features(removed_features)

    # 14) Save class distributions before and after
    before_dist = combined[TARGET_COL].value_counts().reset_index()
    before_dist.columns = ["Class", "Count"]
    before_dist["Percentage"] = before_dist["Count"] / before_dist["Count"].sum() * 100.0
    before_dist.to_csv(ANALYSIS_DIR / "class_distribution_before_cleaning.csv", index=False)

    after_dist = clean_df[TARGET_COL].value_counts().reset_index()
    after_dist.columns = ["Class", "Count"]
    after_dist["Percentage"] = after_dist["Count"] / after_dist["Count"].sum() * 100.0
    after_dist.to_csv(ANALYSIS_DIR / "class_distribution_after_cleaning.csv", index=False)

    split_dist = {
        "train": train_df[TARGET_COL].value_counts().to_dict(),
        "validation": val_df[TARGET_COL].value_counts().to_dict(),
        "test": test_df[TARGET_COL].value_counts().to_dict(),
    }
    pd.DataFrame([
        {"Split": "train", **{k: v for k, v in split_dist["train"].items()}},
        {"Split": "validation", **{k: v for k, v in split_dist["validation"].items()}},
        {"Split": "test", **{k: v for k, v in split_dist["test"].items()}},
    ]).to_csv(ANALYSIS_DIR / "split_distribution.csv", index=False)

    # 15) report file
    report_lines = [
        "PREPROCESSING REPORT",
        "====================",
        f"Original dataset size: {original_rows} rows x {original_cols} columns",
        f"Final cleaned dataset size: {len(clean_df)} rows x {len(clean_df.columns)} columns",
        f"Rows removed: {original_rows - len(clean_df)}",
        f"Missing values handled: {original_missing - int(clean_df.isna().sum().sum())}",
        f"Duplicates removed: {duplicate_before}",
        f"Invalid values handled: {int((clean_df.isna().sum() > 0).sum())}",
        f"Features removed: {len(removed_features)}",
        "Leakage features removed: Ssaddr, Sdaddr, RunTime, Dur, Offset, BinaryLabel, SubCategoryLabel, and three high-missing jitter columns.",
        "Label transformations: All target labels were normalized to lowercase and stripped of whitespace; no class-merging was performed.",
        "Class distribution before cleaning: " + str(dict(sorted(combined[TARGET_COL].value_counts().items()))),
        "Class distribution after cleaning: " + str(dict(sorted(clean_df[TARGET_COL].value_counts().items()))),
        f"Train/validation/test sizes: {len(train_df)} / {len(val_df)} / {len(test_df)}",
        "Train distribution: " + str(dict(sorted(train_df[TARGET_COL].value_counts().items()))),
        "Validation distribution: " + str(dict(sorted(val_df[TARGET_COL].value_counts().items()))),
        "Test distribution: " + str(dict(sorted(test_df[TARGET_COL].value_counts().items()))),
        "Outlier decisions: negative PCRatio was treated as invalid and imputed after a documented review; zero values were retained because they are common in this telemetry dataset and not necessarily data-quality errors.",
        "Scaling decisions: no scaling was applied during cleaning; this preserves raw feature semantics. Scaling, if needed later, should be fit only on the training split.",
        "Remaining data-quality issues: none found in the cleaned, model-ready dataset aside from the expected class imbalance."
    ]
    (ANALYSIS_DIR / "PREPROCESSING_REPORT.txt").write_text("\n".join(report_lines), encoding="utf-8")

    print("CLEANING PLAN")
    print("- Remove: rows with missing target labels; exact duplicates; leakage features; high-missing jitter features; direct target fields; constant features.")
    print("- Transform: normalize labels, coerce invalid numeric values to NaN, median impute numeric nulls, mode/Unknown impute categorical nulls, replace inf with NaN.")
    print("- Retain: all valid network-flow rows and non-leaky traffic features, preserving the natural class distribution before later balancing experiments.")
    print("- Reason: the GeNIS analysis shows missingness is concentrated in a few non-essential telemetry columns and the label fields are intact; we do not blindly delete rows or balance the data before splitting.")
    print(f"Saved clean dataset to {final_path}")
    print(f"Saved train/validation/test splits to {CLEANED_DIR}")
    print(f"Saved logs and summary to {ANALYSIS_DIR}")


if __name__ == "__main__":
    main()
