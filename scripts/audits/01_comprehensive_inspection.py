"""
COMPREHENSIVE INSPECTION OF TNEA CUTOFF MASTER DATASET
Before final cleanup - verify all issues and variations
"""

import pandas as pd
import numpy as np
from pathlib import Path
from collections import Counter

# Load dataset
master_file = Path(__file__).resolve().parents[2] / 'data' / 'cleaned' / 'cutoff' / 'tnea_cutoff_master.csv'
df = pd.read_csv(master_file)

print("="*80)
print("COMPREHENSIVE DATASET INSPECTION")
print("="*80)

# 1. BASIC STATISTICS
print("\n1. BASIC STATISTICS")
print("-"*80)
print(f"Total rows: {len(df):,}")
print(f"Total columns: {len(df.columns)}")
print(f"Memory usage: {df.memory_usage(deep=True).sum()/1024/1024:.2f} MB")

# 2. MISSING VALUES
print("\n2. MISSING VALUES")
print("-"*80)
missing = df.isnull().sum()
for col in df.columns:
    if missing[col] > 0:
        pct = 100 * missing[col] / len(df)
        print(f"{col:<20} {missing[col]:>6,} ({pct:>5.1f}%)")

# 3. DUPLICATES
print("\n3. DUPLICATE ANALYSIS")
print("-"*80)
exact_dups = df.duplicated().sum()
print(f"Exact duplicate rows: {exact_dups}")

logical_dups = df.duplicated(subset=['year', 'college_code', 'branch_code']).sum()
print(f"Logical duplicates (year+college+branch): {logical_dups}")

# 4. UNIQUE VALUES
print("\n4. UNIQUE VALUES")
print("-"*80)
print(f"Unique years: {sorted(df['year'].unique())}")
print(f"Unique college codes: {df['college_code'].nunique()}")
print(f"Unique branch codes: {df['branch_code'].nunique()}")
print(f"Unique districts: {df['district'].nunique()}")
print(f"Unique branch names: {df['branch_name'].nunique()}")

# 5. BRANCH NAMES - Detailed Analysis
print("\n5. BRANCH NAMES - DETAILED ANALYSIS")
print("-"*80)
print(f"Total branch names: {df['branch_name'].nunique()}")

# Group by branch_code and collect unique names
branch_name_variants = {}
for code in sorted(df['branch_code'].unique()):
    names = sorted(df[df['branch_code'] == code]['branch_name'].unique())
    if len(names) > 1:
        branch_name_variants[code] = names

if branch_name_variants:
    print(f"\n⚠ Branch codes with MULTIPLE names ({len(branch_name_variants)}):")
    for code, names in sorted(branch_name_variants.items()):
        print(f"\n  {code}:")
        for name in names:
            count = len(df[df['branch_name'] == name])
            print(f"    - {name} ({count} records)")
else:
    print("✓ No branch codes with multiple names")

# 6. DISTRICTS
print("\n6. DISTRICT VALUES")
print("-"*80)
districts = sorted(df['district'].unique())
print(f"Total unique districts: {len(districts)}")
print(f"\nAll districts:")
for dist in districts:
    count = len(df[df['district'] == dist])
    print(f"  {dist:<20} ({count:>5} records)")

# Check for suspicious variations
district_lower = df['district'].str.lower().unique()
if len(district_lower) < len(districts):
    print("\n⚠ WARNING: Potential district name case variations")
    for dist in districts:
        if dist.lower() in district_lower:
            similar = [d for d in districts if d.lower() == dist.lower()]
            if len(similar) > 1:
                print(f"  Variants of '{dist}':")
                for s in similar:
                    count = len(df[df['district'] == s])
                    print(f"    - {s} ({count} records)")

# 7. COLLEGE CODE 1511 INSPECTION
print("\n7. COLLEGE CODE 1511 INSPECTION")
print("-"*80)
code_1511 = df[df['college_code'] == 1511]
if len(code_1511) > 0:
    print(f"Found {len(code_1511)} records with college_code 1511")
    print(f"\nYears: {sorted(code_1511['year'].unique())}")
    
    for year in sorted(code_1511['year'].unique()):
        year_data = code_1511[code_1511['year'] == year]
        print(f"\n  Year {year}: {len(year_data)} records")
        
        # Check for name variations
        unique_names = year_data['college_name'].unique()
        if len(unique_names) > 1:
            print(f"  ⚠ Multiple college names found ({len(unique_names)}):")
            for name in unique_names:
                count = len(year_data[year_data['college_name'] == name])
                print(f"    - {name[:60]}... ({count} records)")
                
                # Show address parts
                name_data = year_data[year_data['college_name'] == name]
                print(f"      Branches: {name_data['branch_code'].nunique()}")
        else:
            print(f"  Single college name (standardized)")
else:
    print("✓ College code 1511 NOT FOUND in dataset")

# 8. SPECIAL CASE: 2023 + 1219 + MR + BC_PARTIAL
print("\n8. SPECIAL CASE: 2023 + college 1219 + branch MR + BC_PARTIAL")
print("-"*80)
special = df[(df['year'] == 2023) & (df['college_code'] == 1219) & (df['branch_code'] == 'MR')]
if len(special) > 0:
    print(f"Found {len(special)} record(s)")
    for idx, row in special.iterrows():
        print(f"\nCollege: {row['college_name']}")
        print(f"Branch: {row['branch_name']}")
        print(f"District: {row['district']}")
        print(f"BC cutoff: {row['bc']}")
        print(f"BC_partial: {row['bc_partial']}")
        if pd.isna(row['bc']) and row['bc_partial'] == 1:
            print("⚠ SUSPICIOUS: BC cutoff missing but bc_partial = 1")
else:
    print("✓ Record NOT FOUND in dataset")

# 9. PARTIAL COLUMNS VALIDATION
print("\n9. PARTIAL COLUMNS VALIDATION")
print("-"*80)
partial_cols = ['oc_partial', 'bc_partial', 'bcm_partial', 'mbc_partial', 'sc_partial', 'sca_partial', 'st_partial']
for col in partial_cols:
    unique_vals = df[col].unique()
    print(f"{col:<20} unique values: {sorted(unique_vals)}")
    
    if not all(v in [0, 1] for v in unique_vals):
        print(f"  ⚠ WARNING: Contains non-binary values!")

# 10. CUTOFF + PARTIAL RELATIONSHIPS
print("\n10. CUTOFF + PARTIAL RELATIONSHIPS")
print("-"*80)
cutoff_cols = ['oc', 'bc', 'bcm', 'mbc', 'sc', 'sca', 'st']
for cutoff, partial in zip(cutoff_cols, partial_cols):
    print(f"\n{cutoff.upper()}:")
    
    has_cutoff = df[cutoff].notna().sum()
    missing_cutoff = df[cutoff].isna().sum()
    
    has_and_partial_0 = len(df[(df[cutoff].notna()) & (df[partial] == 0)])
    has_and_partial_1 = len(df[(df[cutoff].notna()) & (df[partial] == 1)])
    missing_and_partial_0 = len(df[(df[cutoff].isna()) & (df[partial] == 0)])
    missing_and_partial_1 = len(df[(df[cutoff].isna()) & (df[partial] == 1)])
    
    print(f"  Cutoff present + partial=0: {has_and_partial_0:>6}")
    print(f"  Cutoff present + partial=1: {has_and_partial_1:>6}")
    print(f"  Cutoff missing + partial=0: {missing_and_partial_0:>6}")
    print(f"  Cutoff missing + partial=1: {missing_and_partial_1:>6}")
    
    if missing_and_partial_1 > 0:
        print(f"  ⚠ SUSPICIOUS: {missing_and_partial_1} records have cutoff missing but partial=1")

# 11. NUMERIC VALIDATION
print("\n11. NUMERIC VALIDATION")
print("-"*80)
for col in cutoff_cols:
    values = df[col].dropna()
    if len(values) > 0:
        neg_count = (values < 0).sum()
        high_count = (values > 200).sum()
        
        print(f"{col.upper()}:")
        print(f"  Valid values: {len(values):>6}")
        print(f"  Min: {values.min():>8.2f}")
        print(f"  Max: {values.max():>8.2f}")
        print(f"  Negative values: {neg_count}")
        print(f"  Values > 200: {high_count}")
        
        if neg_count > 0 or high_count > 0:
            print(f"  ⚠ SUSPICIOUS VALUES FOUND")

# 12. YEAR VALIDATION
print("\n12. YEAR VALIDATION")
print("-"*80)
years = sorted(df['year'].unique())
print(f"Years in dataset: {years}")
expected_years = [2021, 2022, 2023, 2024, 2025]
if years == expected_years:
    print("✓ Correct years")
else:
    print(f"⚠ WARNING: Expected {expected_years}, got {years}")

# 13. REQUIRED IDENTIFIERS
print("\n13. REQUIRED IDENTIFIERS")
print("-"*80)
print(f"Missing college_code: {df['college_code'].isna().sum()}")
print(f"Missing branch_code: {df['branch_code'].isna().sum()}")
print(f"Missing college_name: {df['college_name'].isna().sum()}")
print(f"Missing branch_name: {df['branch_name'].isna().sum()}")

# 14. SAMPLE VARIATIONS
print("\n14. SAMPLE BRANCH NAME VARIATIONS (if any)")
print("-"*80)
if branch_name_variants:
    for code, names in list(branch_name_variants.items())[:3]:
        print(f"\nBranch code '{code}':")
        for name in names[:2]:
            print(f"  - {name}")
else:
    print("No name variations found for any branch code")

print("\n" + "="*80)
print("INSPECTION COMPLETE")
print("="*80)
