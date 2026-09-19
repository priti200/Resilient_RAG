# =============================================================
# GeNIS Preprocessing
# - Preserve original GeNIS train/test partition
# - Create validation split from original training data only
# - Fit imputation statistics on training data only
# - Apply identical preprocessing to train/validation/test
# =============================================================

import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

# =============================================================
# PATHS
# =============================================================

BASE_DIR = Path(__file__).resolve().parent
ORIGINAL_DIR = BASE_DIR / "data" / "original"
CLEANED_DIR = BASE_DIR / "data" / "cleaned"
ANALYSIS_DIR = BASE_DIR / "analysis_results"

ORIGINAL_DIR.mkdir(parents=True, exist_ok=True)
CLEANED_DIR.mkdir(parents=True, exist_ok=True)
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================
# CONFIGURATION
# =============================================================

TARGET_COL = "CategoryLabel"
BINARY_COL = "BinaryLabel"
SUBCATEGORY_COL = "SubCategoryLabel"

HIGH_MISSING_COLUMNS = [
    "DstJitAct",
    "DstJitter",
    "SrcJitAct",
]

POTENTIAL_LEAKAGE_FEATURES = [
    "Ssaddr",
    "Sdaddr",
    "RunTime",
    "Dur",
    "Offset",
]

RANDOM_STATE = 42
VALIDATION_SIZE = 0.15


# =============================================================
# HELPERS
# =============================================================


def log_step(log_rows, step, description, rows=None, columns=None):
    """Add an entry to the cleaning log."""

    log_rows.append(
        {
            "Step": step,
            "Description": description,
            "Rows": rows,
            "Columns": columns,
        }
    )


def standardize_columns(df):
    """Standardize column names."""

    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]

    return df


def normalize_labels(df):
    """Normalize the target labels."""

    df = df.copy()

    if TARGET_COL in df.columns:
        df[TARGET_COL] = df[TARGET_COL].astype(str).str.strip().str.lower()

        # Handle common naming variations if present.
        label_mapping = {
            "benign": "benign",
            "dos": "dos",
            "denial of service": "dos",
            "bruteforce": "bruteforce",
            "brute force": "bruteforce",
            "recon": "recon",
            "reconnaissance": "recon",
        }

        df[TARGET_COL] = df[TARGET_COL].replace(label_mapping)

    return df


def structural_clean(
    df,
    log_rows,
    split_name,
    columns_to_remove=None,
):
    """
    Perform cleaning that does not require statistics learned
    from the data.

    Important:
    - No imputation happens here.
    - No statistics are learned here.
    """

    df = df.copy()

    # ---------------------------------------------------------
    # Standardize column names
    # ---------------------------------------------------------

    df = standardize_columns(df)

    log_step(
        log_rows,
        f"{split_name}:standardize_columns",
        "Standardized column names",
        len(df),
        len(df.columns),
    )

    # ---------------------------------------------------------
    # Normalize labels
    # ---------------------------------------------------------

    df = normalize_labels(df)

    # ---------------------------------------------------------
    # Remove rows with missing target
    # ---------------------------------------------------------

    if TARGET_COL in df.columns:
        before = len(df)

        df = df.dropna(subset=[TARGET_COL]).copy()

        removed = before - len(df)

        log_step(
            log_rows,
            f"{split_name}:missing_target",
            f"Removed {removed} rows with missing target",
            len(df),
            len(df.columns),
        )

    # ---------------------------------------------------------
    # Remove predefined high-missing columns
    # ---------------------------------------------------------

    high_missing_to_remove = [col for col in HIGH_MISSING_COLUMNS if col in df.columns]

    if high_missing_to_remove:
        df = df.drop(columns=high_missing_to_remove)

        log_step(
            log_rows,
            f"{split_name}:high_missing_columns",
            "Removed predefined high-missing columns: "
            + ", ".join(high_missing_to_remove),
            len(df),
            len(df.columns),
        )

    # ---------------------------------------------------------
    # Remove potential leakage / identifier columns
    # ---------------------------------------------------------

    leakage_to_remove = [col for col in POTENTIAL_LEAKAGE_FEATURES if col in df.columns]

    if leakage_to_remove:
        df = df.drop(columns=leakage_to_remove)

        log_step(
            log_rows,
            f"{split_name}:leakage_features",
            "Removed potential leakage features: " + ", ".join(leakage_to_remove),
            len(df),
            len(df.columns),
        )

    # ---------------------------------------------------------
    # Remove direct binary/subcategory labels
    # ---------------------------------------------------------

    target_related_to_remove = [
        col
        for col in [
            BINARY_COL,
            SUBCATEGORY_COL,
        ]
        if col in df.columns
    ]

    if target_related_to_remove:
        df = df.drop(columns=target_related_to_remove)

        log_step(
            log_rows,
            f"{split_name}:target_related_features",
            "Removed target-related columns: " + ", ".join(target_related_to_remove),
            len(df),
            len(df.columns),
        )

    # ---------------------------------------------------------
    # Convert numeric columns
    # ---------------------------------------------------------

    numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()

    for col in numeric_columns:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce",
        )

    # ---------------------------------------------------------
    # Replace infinite values
    # ---------------------------------------------------------

    numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()

    if numeric_columns:
        df[numeric_columns] = df[numeric_columns].replace(
            [np.inf, -np.inf],
            np.nan,
        )

    # ---------------------------------------------------------
    # Handle invalid PCRatio values
    # ---------------------------------------------------------

    if "PCRatio" in df.columns:
        invalid_pcratio = df["PCRatio"] < 0

        count_invalid = int(invalid_pcratio.sum())

        if count_invalid > 0:
            df.loc[invalid_pcratio, "PCRatio"] = np.nan

            log_step(
                log_rows,
                f"{split_name}:invalid_pcratio",
                f"Converted {count_invalid} negative PCRatio values to missing",
                len(df),
                len(df.columns),
            )

    # ---------------------------------------------------------
    # Remove duplicate rows
    # ---------------------------------------------------------

    before = len(df)

    df = df.drop_duplicates().copy()

    removed_duplicates = before - len(df)

    log_step(
        log_rows,
        f"{split_name}:duplicates",
        f"Removed {removed_duplicates} duplicate rows",
        len(df),
        len(df.columns),
    )

    return df


def determine_constant_columns(train_df):
    """
    Determine constant columns using TRAINING data only.

    These same columns are removed from validation and test.
    """

    constant_columns = []

    for col in train_df.columns:
        if col == TARGET_COL:
            continue

        if train_df[col].nunique(dropna=False) <= 1:
            constant_columns.append(col)

    return constant_columns


def remove_columns(df, columns):
    """Remove columns if they exist."""

    columns_present = [col for col in columns if col in df.columns]

    if columns_present:
        df = df.drop(columns=columns_present)

    return df


def fit_imputation_values(train_df):
    """
    Calculate imputation statistics ONLY from training data.

    Returns:
        numeric_medians
        categorical_modes
    """

    numeric_medians = {}
    categorical_modes = {}

    feature_columns = [col for col in train_df.columns if col != TARGET_COL]

    for col in feature_columns:
        if pd.api.types.is_numeric_dtype(train_df[col]):
            median_value = train_df[col].median()

            # If the entire column is missing,
            # fall back to 0.
            if pd.isna(median_value):
                median_value = 0

            numeric_medians[col] = median_value

        else:
            mode = train_df[col].mode(dropna=True)

            if len(mode) > 0:
                categorical_modes[col] = mode.iloc[0]

            else:
                categorical_modes[col] = "Unknown"

    return numeric_medians, categorical_modes


def apply_imputation(
    df,
    numeric_medians,
    categorical_modes,
    split_name,
    log_rows,
):
    """
    Apply training-fitted imputation statistics.
    """

    df = df.copy()

    # ---------------------------------------------------------
    # Numeric imputation
    # ---------------------------------------------------------

    for col, value in numeric_medians.items():
        if col in df.columns:
            df[col] = df[col].fillna(value)

    # ---------------------------------------------------------
    # Categorical imputation
    # ---------------------------------------------------------

    for col, value in categorical_modes.items():
        if col in df.columns:
            df[col] = df[col].fillna(value)

    # ---------------------------------------------------------
    # Final fallback
    # ---------------------------------------------------------

    remaining_missing = int(df.isna().sum().sum())

    if remaining_missing > 0:
        # Any remaining numeric NaNs
        # should already have been handled.
        # This is just a safety net.

        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()

        if numeric_columns:
            df[numeric_columns] = df[numeric_columns].fillna(0)

        categorical_columns = [col for col in df.columns if col not in numeric_columns]

        for col in categorical_columns:
            if col != TARGET_COL:
                df[col] = df[col].fillna("Unknown")

    remaining_missing = int(df.isna().sum().sum())

    log_step(
        log_rows,
        f"{split_name}:imputation",
        f"Applied train-fitted imputation; remaining missing values: {remaining_missing}",
        len(df),
        len(df.columns),
    )

    return df


def save_distribution(
    df,
    split_name,
):
    """Save target-class distribution."""

    if TARGET_COL not in df.columns:
        return

    distribution = (
        df[TARGET_COL]
        .value_counts(dropna=False)
        .rename_axis(TARGET_COL)
        .reset_index(name="Count")
    )

    distribution["Percentage"] = distribution["Count"] / len(df) * 100

    output_path = ANALYSIS_DIR / f"{split_name}_distribution.csv"

    distribution.to_csv(
        output_path,
        index=False,
    )


def save_summary(
    train_df,
    validation_df,
    test_df,
):
    """Save final dataset summary."""

    summary = pd.DataFrame(
        [
            {
                "Split": "train",
                "Rows": len(train_df),
                "Columns": len(train_df.columns),
                "MissingValues": int(train_df.isna().sum().sum()),
                "Duplicates": int(train_df.duplicated().sum()),
            },
            {
                "Split": "validation",
                "Rows": len(validation_df),
                "Columns": len(validation_df.columns),
                "MissingValues": int(validation_df.isna().sum().sum()),
                "Duplicates": int(validation_df.duplicated().sum()),
            },
            {
                "Split": "test",
                "Rows": len(test_df),
                "Columns": len(test_df.columns),
                "MissingValues": int(test_df.isna().sum().sum()),
                "Duplicates": int(test_df.duplicated().sum()),
            },
        ]
    )

    summary.to_csv(
        ANALYSIS_DIR / "dataset_summary.csv",
        index=False,
    )


# =============================================================
# MAIN
# =============================================================


def main():

    print("=" * 70)
    print("GeNIS preprocessing")
    print("=" * 70)

    # ---------------------------------------------------------
    # Check input directory
    # ---------------------------------------------------------

    if not ORIGINAL_DIR.exists():
        raise FileNotFoundError(f"Original data directory not found:\n{ORIGINAL_DIR}")

    # ---------------------------------------------------------
    # Find the eight GeNIS CSV files
    # ---------------------------------------------------------

    csv_files = sorted(ORIGINAL_DIR.glob("genis-*.csv"))

    train_files = [f for f in csv_files if "-train.csv" in f.name.lower()]

    test_files = [f for f in csv_files if "-test.csv" in f.name.lower()]

    print("\nOriginal train files:")

    for f in train_files:
        print(f"  {f.name}")

    print("\nOriginal test files:")

    for f in test_files:
        print(f"  {f.name}")

    # ---------------------------------------------------------
    # Validate file discovery
    # ---------------------------------------------------------

    if len(train_files) == 0:
        raise FileNotFoundError(
            f"No GeNIS training CSV files were found in:\n{ORIGINAL_DIR}"
        )

    if len(test_files) == 0:
        raise FileNotFoundError(
            f"No GeNIS test CSV files were found in:\n{ORIGINAL_DIR}"
        )

    print(
        f"\nFound {len(train_files)} training files and {len(test_files)} test files."
    )

    # ---------------------------------------------------------
    # Read original TRAIN files
    # ---------------------------------------------------------

    print("\nLoading original training data...")

    train_dfs = []

    for file_path in train_files:
        print(f"  Reading {file_path.name}...")

        df = pd.read_csv(
            file_path,
            low_memory=False,
        )

        print(f"    Rows: {len(df):,} | Columns: {len(df.columns)}")

        train_dfs.append(df)

    original_train = pd.concat(
        train_dfs,
        ignore_index=True,
    )

    del train_dfs

    print(
        f"\nCombined original train: "
        f"{len(original_train):,} rows, "
        f"{len(original_train.columns)} columns"
    )

    # ---------------------------------------------------------
    # Read original TEST files
    # ---------------------------------------------------------

    print("\nLoading original test data...")

    test_dfs = []

    for file_path in test_files:
        print(f"  Reading {file_path.name}...")

        df = pd.read_csv(
            file_path,
            low_memory=False,
        )

        print(f"    Rows: {len(df):,} | Columns: {len(df.columns)}")

        test_dfs.append(df)

    original_test = pd.concat(
        test_dfs,
        ignore_index=True,
    )

    del test_dfs

    print(
        f"\nCombined original test: "
        f"{len(original_test):,} rows, "
        f"{len(original_test.columns)} columns"
    )

    # ---------------------------------------------------------
    # Initial logs
    # ---------------------------------------------------------

    train_log = []
    test_log = []

    log_step(
        train_log,
        "original",
        "Original GeNIS training data",
        len(original_train),
        len(original_train.columns),
    )

    log_step(
        test_log,
        "original",
        "Original GeNIS test data",
        len(original_test),
        len(original_test.columns),
    )

    # ---------------------------------------------------------
    # Structural cleaning
    # ---------------------------------------------------------

    print("\n" + "=" * 70)
    print("STRUCTURAL CLEANING")
    print("=" * 70)

    print("\nCleaning original training data...")

    cleaned_train_pool = structural_clean(
        original_train,
        train_log,
        "train",
    )

    del original_train

    print(
        f"Cleaned training pool: "
        f"{len(cleaned_train_pool):,} rows, "
        f"{len(cleaned_train_pool.columns)} columns"
    )

    print("\nCleaning original test data...")

    cleaned_test = structural_clean(
        original_test,
        test_log,
        "test",
    )

    del original_test

    print(
        f"Cleaned test: {len(cleaned_test):,} rows, {len(cleaned_test.columns)} columns"
    )

    # ---------------------------------------------------------
    # Determine constant columns using TRAIN ONLY
    # ---------------------------------------------------------

    print("\nDetermining constant columns from training data...")

    constant_columns = determine_constant_columns(cleaned_train_pool)

    if constant_columns:
        print(f"Removing {len(constant_columns)} constant columns:")

        for col in constant_columns:
            print(f"  {col}")

        cleaned_train_pool = remove_columns(
            cleaned_train_pool,
            constant_columns,
        )

        cleaned_test = remove_columns(
            cleaned_test,
            constant_columns,
        )

        train_log.append(
            {
                "Step": "train:constant_columns",
                "Description": (
                    "Removed constant columns based on "
                    "training data: " + ", ".join(constant_columns)
                ),
                "Rows": len(cleaned_train_pool),
                "Columns": len(cleaned_train_pool.columns),
            }
        )

        test_log.append(
            {
                "Step": "test:constant_columns",
                "Description": (
                    "Applied constant-column removal "
                    "learned from training data: " + ", ".join(constant_columns)
                ),
                "Rows": len(cleaned_test),
                "Columns": len(cleaned_test.columns),
            }
        )

    # ---------------------------------------------------------
    # Make sure train/test have identical feature columns
    # ---------------------------------------------------------

    train_columns = set(cleaned_train_pool.columns)

    test_columns = set(cleaned_test.columns)

    # Columns present in train but not test
    train_only = sorted(train_columns - test_columns)

    # Columns present in test but not train
    test_only = sorted(test_columns - train_columns)

    if train_only:
        print("\nColumns only present in training data:")

        for col in train_only:
            print(f"  {col}")

    if test_only:
        print("\nColumns only present in test data:")

        for col in test_only:
            print(f"  {col}")

    # Use the intersection of feature columns.
    # Target must remain.
    common_columns = [
        col for col in cleaned_train_pool.columns if col in cleaned_test.columns
    ]

    if TARGET_COL not in common_columns:
        raise ValueError(
            f"{TARGET_COL} is missing from the common training/test schema."
        )

    cleaned_train_pool = cleaned_train_pool[common_columns].copy()

    cleaned_test = cleaned_test[common_columns].copy()

    print(f"\nFinal common schema: {len(common_columns)} columns")

    # ---------------------------------------------------------
    # Split ORIGINAL TRAIN into train/validation
    # ---------------------------------------------------------

    print("\n" + "=" * 70)
    print("TRAIN / VALIDATION SPLIT")
    print("=" * 70)

    if TARGET_COL not in cleaned_train_pool.columns:
        raise ValueError(f"{TARGET_COL} not found in training data.")

    print(
        "\nSplitting original GeNIS training data "
        f"into {1 - VALIDATION_SIZE:.0%} train / "
        f"{VALIDATION_SIZE:.0%} validation..."
    )

    train_df, validation_df = train_test_split(
        cleaned_train_pool,
        test_size=VALIDATION_SIZE,
        stratify=cleaned_train_pool[TARGET_COL],
        random_state=RANDOM_STATE,
    )

    train_df = train_df.reset_index(drop=True)

    validation_df = validation_df.reset_index(drop=True)

    cleaned_test = cleaned_test.reset_index(drop=True)

    del cleaned_train_pool

    print(f"Train:       {len(train_df):,} rows")

    print(f"Validation:  {len(validation_df):,} rows")

    print(f"Test:        {len(cleaned_test):,} rows (original GeNIS test)")

    # ---------------------------------------------------------
    # Fit imputation ONLY on training data
    # ---------------------------------------------------------

    print("\n" + "=" * 70)
    print("TRAIN-ONLY IMPUTATION")
    print("=" * 70)

    print("\nCalculating imputation statistics from TRAINING DATA ONLY...")

    numeric_medians, categorical_modes = fit_imputation_values(train_df)

    print(f"Numeric columns with medians: {len(numeric_medians)}")

    print(f"Categorical columns with modes: {len(categorical_modes)}")

    # ---------------------------------------------------------
    # Apply train-fitted imputation
    # ---------------------------------------------------------

    print("\nApplying imputation to train...")

    train_df = apply_imputation(
        train_df,
        numeric_medians,
        categorical_modes,
        "train",
        train_log,
    )

    print("Applying imputation to validation...")

    validation_df = apply_imputation(
        validation_df,
        numeric_medians,
        categorical_modes,
        "validation",
        train_log,
    )

    print("Applying imputation to test...")

    cleaned_test = apply_imputation(
        cleaned_test,
        numeric_medians,
        categorical_modes,
        "test",
        test_log,
    )

    # ---------------------------------------------------------
    # Final validation checks
    # ---------------------------------------------------------

    print("\n" + "=" * 70)
    print("FINAL CHECKS")
    print("=" * 70)

    datasets = {
        "train": train_df,
        "validation": validation_df,
        "test": cleaned_test,
    }

    for name, df in datasets.items():
        missing = int(df.isna().sum().sum())

        infinite = 0

        numeric_columns = df.select_dtypes(include=[np.number]).columns

        if len(numeric_columns) > 0:
            infinite = int(np.isinf(df[numeric_columns].to_numpy()).sum())

        duplicates = int(df.duplicated().sum())

        print(f"\n{name.upper()}:")

        print(f"  Rows:        {len(df):,}")

        print(f"  Columns:     {len(df.columns)}")

        print(f"  Missing:     {missing}")

        print(f"  Infinite:    {infinite}")

        print(f"  Duplicates:  {duplicates}")

        if TARGET_COL in df.columns:
            print(f"  Classes:     {df[TARGET_COL].nunique()}")

            print(df[TARGET_COL].value_counts().to_string())

        if missing != 0:
            raise ValueError(f"{name} still contains missing values.")

        if infinite != 0:
            raise ValueError(f"{name} still contains infinite values.")

    # ---------------------------------------------------------
    # Save processed datasets
    # ---------------------------------------------------------

    print("\n" + "=" * 70)
    print("SAVING DATASETS")
    print("=" * 70)

    train_path = CLEANED_DIR / "train.csv"
    validation_path = CLEANED_DIR / "validation.csv"
    test_path = CLEANED_DIR / "test.csv"

    print(f"\nSaving train → {train_path}")

    train_df.to_csv(
        train_path,
        index=False,
    )

    print(f"Saving validation → {validation_path}")

    validation_df.to_csv(
        validation_path,
        index=False,
    )

    print(f"Saving test → {test_path}")

    cleaned_test.to_csv(
        test_path,
        index=False,
    )

    # ---------------------------------------------------------
    # Save combined cleaned dataset
    # ---------------------------------------------------------

    print("\nSaving combined cleaned dataset...")

    combined_cleaned = pd.concat(
        [
            train_df,
            validation_df,
            cleaned_test,
        ],
        ignore_index=True,
    )

    combined_path = CLEANED_DIR / "combined_cleaned.csv"

    combined_cleaned.to_csv(
        combined_path,
        index=False,
    )

    del combined_cleaned

    # ---------------------------------------------------------
    # Save distributions
    # ---------------------------------------------------------

    save_distribution(
        train_df,
        "train",
    )

    save_distribution(
        validation_df,
        "validation",
    )

    save_distribution(
        cleaned_test,
        "test",
    )

    # ---------------------------------------------------------
    # Save cleaning logs
    # ---------------------------------------------------------

    all_logs = train_log + test_log

    cleaning_log_df = pd.DataFrame(all_logs)

    cleaning_log_df.to_csv(
        ANALYSIS_DIR / "cleaning_log.csv",
        index=False,
    )

    # ---------------------------------------------------------
    # Save removed feature list
    # ---------------------------------------------------------

    removed_features = []

    for col in HIGH_MISSING_COLUMNS:
        if col in HIGH_MISSING_COLUMNS:
            removed_features.append(
                {
                    "Feature": col,
                    "Reason": "High missingness",
                }
            )

    for col in POTENTIAL_LEAKAGE_FEATURES:
        removed_features.append(
            {
                "Feature": col,
                "Reason": "Potential leakage / identifier",
            }
        )

    for col in [
        BINARY_COL,
        SUBCATEGORY_COL,
    ]:
        removed_features.append(
            {
                "Feature": col,
                "Reason": "Target-related feature",
            }
        )

    for col in constant_columns:
        removed_features.append(
            {
                "Feature": col,
                "Reason": "Constant in training data",
            }
        )

    pd.DataFrame(removed_features).drop_duplicates(subset=["Feature"]).to_csv(
        ANALYSIS_DIR / "removed_features.csv",
        index=False,
    )

    # ---------------------------------------------------------
    # Save summary
    # ---------------------------------------------------------

    save_summary(
        train_df,
        validation_df,
        cleaned_test,
    )

    # ---------------------------------------------------------
    # Final output
    # ---------------------------------------------------------

    print("\n" + "=" * 70)
    print("PREPROCESSING COMPLETE")
    print("=" * 70)

    print(f"\nOutput directory:\n  {CLEANED_DIR}")

    print("\nGenerated:")

    print(f"  train.csv        : {len(train_df):,} rows")

    print(f"  validation.csv   : {len(validation_df):,} rows")

    print(f"  test.csv         : {len(cleaned_test):,} rows")

    print("\nImportant:")
    print("  - Original GeNIS test partition was preserved.")
    print("  - Validation was created only from original training data.")
    print("  - Imputation statistics were fitted only on training data.")

    print("  - The same training-fitted imputation was applied to validation/test.")

    print("=" * 70)


if __name__ == "__main__":
    main()
