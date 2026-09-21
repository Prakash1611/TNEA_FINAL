"""
TNEA CUTOFF DATA INSPECTION SCRIPT
Inspects raw CSV files before cleaning
"""

import pandas as pd
import os
from pathlib import Path

# Configuration
ROOT = Path(__file__).resolve().parents[2]
DATA_CUTOFF_PATH = ROOT / 'data' / 'raw' / 'cutoff'
OUTPUT_PATH = ROOT / 'documentation' / 'inspection_report.txt'

# Years to process
YEARS = [2021, 2022, 2023, 2024, 2025]

# Load all files
datasets = {}
for year in YEARS:
    file_path = DATA_CUTOFF_PATH / f'tnea_{year}.csv'
    datasets[year] = pd.read_csv(file_path)
    print(f"✓ Loaded {year} data: {len(datasets[year])} rows")

# Generate inspection report
report = []

report.append("=" * 70)
report.append("TNEA CUTOFF DATA INSPECTION REPORT")
report.append("=" * 70)
report.append("")

# ===== YEAR SUMMARY =====
report.append("YEAR SUMMARY")
report.append("-" * 70)
for year in YEARS:
    df = datasets[year]
    report.append(f"\n{year}:")
    report.append(f"  Raw rows:        {len(df)}")
    report.append(f"  Columns:         {len(df.columns)}")
    report.append(f"  Exact duplicates: {df.duplicated().sum()}")
    
    # Logical duplicates (college_code + branch_code)
    if 'college_code' in df.columns and 'branch_code' in df.columns:
        logical_dups = df.duplicated(subset=['college_code', 'branch_code']).sum()
        report.append(f"  Logical duplicates (college+branch): {logical_dups}")
    
    # Unique values
    if 'college_code' in df.columns:
        report.append(f"  Unique colleges: {df['college_code'].nunique()}")
    if 'branch_code' in df.columns:
        report.append(f"  Unique branches: {df['branch_code'].nunique()}")

report.append("")

# ===== COLUMN STRUCTURE =====
report.append("COLUMN STRUCTURE")
report.append("-" * 70)

# Check if all years have same columns
all_columns = [set(datasets[year].columns) for year in YEARS]
if all(col == all_columns[0] for col in all_columns):
    report.append("✓ All years have IDENTICAL column structure")
    report.append("")
    report.append("Columns (20 total):")
    for i, col in enumerate(datasets[2021].columns, 1):
        report.append(f"  {i:2d}. {col}")
else:
    report.append("✗ Column structure DIFFERS between years!")
    report.append("")
    for year in YEARS:
        report.append(f"\n{year} columns ({len(datasets[year].columns)}):")
        for i, col in enumerate(datasets[year].columns, 1):
            report.append(f"  {i:2d}. {col}")

report.append("")

# ===== DATA TYPES =====
report.append("DATA TYPES BY YEAR")
report.append("-" * 70)
for year in YEARS:
    report.append(f"\n{year}:")
    report.append(f"  {datasets[year].dtypes.to_string()}")

report.append("")

# ===== MISSING VALUES =====
report.append("MISSING VALUES BY COLUMN AND YEAR")
report.append("-" * 70)

# Get all columns from first dataset
columns = datasets[2021].columns.tolist()

report.append("\nFormat: column_name | 2021 | 2022 | 2023 | 2024 | 2025")
report.append("-" * 70)

for col in columns:
    missing_counts = []
    for year in YEARS:
        missing = datasets[year][col].isna().sum()
        missing_counts.append(missing)
    
    # Only show columns with missing values
    if any(c > 0 for c in missing_counts):
        counts_str = " | ".join(str(c) for c in missing_counts)
        report.append(f"{col:<30} | {counts_str}")

report.append("")

# ===== NUMERIC CUTOFF COLUMNS ANALYSIS =====
report.append("NUMERIC CUTOFF COLUMNS ANALYSIS")
report.append("-" * 70)

# Identify cutoff columns (assuming: oc, bc, bcm, mbc, sc, sca, st)
cutoff_cols = [col for col in columns if col in ['oc', 'bc', 'bcm', 'mbc', 'sc', 'sca', 'st']]
partial_cutoff_cols = [col for col in columns if 'partial' in col]

report.append(f"\nMain cutoff columns found: {', '.join(cutoff_cols)}")
report.append(f"Partial cutoff columns found: {len(partial_cutoff_cols)}")

for year in YEARS:
    report.append(f"\n{year} Cutoff Value Statistics:")
    report.append("-" * 50)
    
    for col in cutoff_cols:
        series = pd.to_numeric(datasets[year][col], errors='coerce')
        missing = series.isna().sum()
        valid = (~series.isna()).sum()
        
        if valid > 0:
            report.append(f"  {col}:")
            report.append(f"    Valid values:  {valid}")
            report.append(f"    Missing:       {missing}")
            report.append(f"    Min:           {series.min():.2f}")
            report.append(f"    Max:           {series.max():.2f}")
            report.append(f"    Mean:          {series.mean():.2f}")

report.append("")

# ===== TEXT COLUMNS INSPECTION =====
report.append("TEXT COLUMNS INSPECTION")
report.append("-" * 70)

text_cols = ['college_name', 'district', 'college_type', 'branch_name']

for col in text_cols:
    if col in datasets[2021].columns:
        report.append(f"\n{col}:")
        for year in YEARS:
            df = datasets[year]
            unique_count = df[col].nunique()
            empty_count = (df[col].str.strip() == '').sum() if df[col].dtype == 'object' else 0
            
            report.append(f"  {year}: {unique_count} unique values, {empty_count} empty")

report.append("")

# ===== UNIQUE VALUES IN KEY COLUMNS =====
report.append("UNIQUE COLLEGES AND BRANCHES")
report.append("-" * 70)

for year in YEARS:
    df = datasets[year]
    
    if 'college_code' in df.columns:
        unique_colleges = df['college_code'].unique()
        report.append(f"\n{year} Unique college codes: {len(unique_colleges)}")
        report.append(f"  Range: {sorted(unique_colleges.astype(str))[:5]}... (showing first 5)")
    
    if 'branch_code' in df.columns:
        unique_branches = df['branch_code'].unique()
        report.append(f"\n{year} Unique branch codes: {len(unique_branches)}")
        branch_list = sorted(unique_branches)
        # Show all branches since there aren't too many
        for i in range(0, len(branch_list), 8):
            report.append(f"  {', '.join(branch_list[i:i+8])}")

report.append("")

# ===== SUSPICIOUS VALUES =====
report.append("SUSPICIOUS VALUES AND ANOMALIES")
report.append("-" * 70)

suspicious = []

for year in YEARS:
    df = datasets[year]
    
    # Check for negative cutoff values
    for col in cutoff_cols:
        series = pd.to_numeric(df[col], errors='coerce')
        neg_count = (series < 0).sum()
        if neg_count > 0:
            suspicious.append(f"{year} {col}: {neg_count} negative values")
    
    # Check for extremely high cutoff values (>200 seems suspicious for admission cutoffs)
    for col in cutoff_cols:
        series = pd.to_numeric(df[col], errors='coerce')
        high_count = (series > 200).sum()
        if high_count > 0:
            max_val = series.max()
            suspicious.append(f"{year} {col}: {high_count} values > 200 (max: {max_val})")
    
    # Check for extremely low cutoff values (<0 already checked)
    for col in cutoff_cols:
        series = pd.to_numeric(df[col], errors='coerce')
        low_count = (series < 50).sum()
        if low_count > 0:
            # Note: This might be valid, just flagging for review
            min_val = series.min()
            suspicious.append(f"{year} {col}: {low_count} values < 50 (min: {min_val})")

if suspicious:
    for item in suspicious:
        report.append(f"  ⚠ {item}")
else:
    report.append("  ✓ No obvious suspicious values detected")

report.append("")

# ===== SCHEMA CONSISTENCY =====
report.append("SCHEMA CONSISTENCY CHECK")
report.append("-" * 70)

all_schemas_same = all(set(datasets[year].columns) == set(datasets[2021].columns) for year in YEARS)
if all_schemas_same:
    report.append("✓ All five years have IDENTICAL schemas")
    report.append("  Column order may differ, but all columns are present in all years")
else:
    report.append("✗ Schema differs between years")
    report.append("  Investigating differences...")
    
    ref_cols = set(datasets[2021].columns)
    for year in YEARS[1:]:
        year_cols = set(datasets[year].columns)
        missing = ref_cols - year_cols
        extra = year_cols - ref_cols
        
        if missing:
            report.append(f"  {year} missing: {missing}")
        if extra:
            report.append(f"  {year} extra: {extra}")

report.append("")

# ===== SAMPLE RECORDS =====
report.append("SAMPLE RECORDS (First row of each year)")
report.append("-" * 70)

for year in YEARS:
    report.append(f"\n{year}:")
    first_row = datasets[year].iloc[0]
    for col in first_row.index[:5]:  # Show first 5 columns as sample
        report.append(f"  {col}: {first_row[col]}")
    report.append("  ...")

report.append("")
report.append("=" * 70)
report.append("END OF INSPECTION REPORT")
report.append("=" * 70)

# Write report to file
report_text = "\n".join(report)
print("\n" + report_text)

with open(OUTPUT_PATH, 'w') as f:
    f.write(report_text)

print(f"\n✓ Report saved to: {OUTPUT_PATH}")
