# Dataset File Inventory

This document lists the key cleaned, split, and balanced dataset files in the project and their exact paths.

## Root project

- Project root: `c:\Users\sdine\OneDrive\Documents\4-preprocessed`

## Original source data

- `c:\Users\sdine\OneDrive\Documents\4-preprocessed\data\original\genis-5-sec-train.csv`
- `c:\Users\sdine\OneDrive\Documents\4-preprocessed\data\original\genis-10-sec-train.csv`
- `c:\Users\sdine\OneDrive\Documents\4-preprocessed\data\original\genis-30-sec-train.csv`
- `c:\Users\sdine\OneDrive\Documents\4-preprocessed\data\original\genis-60-sec-train.csv`
- `c:\Users\sdine\OneDrive\Documents\4-preprocessed\data\original\genis-5-sec-test.csv`
- `c:\Users\sdine\OneDrive\Documents\4-preprocessed\data\original\genis-10-sec-test.csv`
- `c:\Users\sdine\OneDrive\Documents\4-preprocessed\data\original\genis-30-sec-test.csv`
- `c:\Users\sdine\OneDrive\Documents\4-preprocessed\data\original\genis-60-sec-test.csv`

## Cleaned data

- Full cleaned unbalanced dataset:
  - `c:\Users\sdine\OneDrive\Documents\4-preprocessed\data\cleaned\GeNIS_cleaned_unbalanced.csv`

- Train split:
  - `c:\Users\sdine\OneDrive\Documents\4-preprocessed\data\cleaned\train.csv`

- Validation split:
  - `c:\Users\sdine\OneDrive\Documents\4-preprocessed\data\cleaned\validation.csv`

- Test split:
  - `c:\Users\sdine\OneDrive\Documents\4-preprocessed\data\cleaned\test.csv`

## Balanced training data

- Balanced training dataset (undersampled to equal class counts):
  - `c:\Users\sdine\OneDrive\Documents\4-preprocessed\data\cleaned\train_balanced.csv`

## Analysis and reports

- Preprocessing report:
  - `c:\Users\sdine\OneDrive\Documents\4-preprocessed\analysis_results\PREPROCESSING_REPORT.txt`

- Balancing report:
  - `c:\Users\sdine\OneDrive\Documents\4-preprocessed\analysis_results\balancing_report.txt`

- Main analysis report:
  - `c:\Users\sdine\OneDrive\Documents\4-preprocessed\ANALYSIS_REPORT.txt`

## Summary

- The cleaned dataset is the standard model-ready data.
- The balanced dataset is a training-only variant used for class-equal training experiments.
- The primary files to use for downstream model development are:
  - `data\cleaned\GeNIS_cleaned_unbalanced.csv`
  - `data\cleaned\train.csv`
  - `data\cleaned\validation.csv`
  - `data\cleaned\test.csv`
  - `data\cleaned\train_balanced.csv`
