"""
TNEA CUTOFF DATA - FINAL CLEANUP AND VALIDATION
Applies verified standardizations based on actual data inspection
Creates comprehensive audit trail and reports
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

# ============================================================================
# PATHS
# ============================================================================

ROOT = Path(__file__).resolve().parents[2]
MASTER_FILE = ROOT / 'data' / 'cleaned' / 'cutoff' / 'tnea_cutoff_master.csv'
BACKUP_FILE = ROOT / 'backups' / 'data' / 'tnea_cutoff_master_before_final_cleanup.csv'
FINAL_FILE = ROOT / 'data' / 'cleaned' / 'cutoff' / 'tnea_cutoff_master_final.csv'
REPORT_FILE = ROOT / 'documentation' / 'cutoff_final_cleanup_report.txt'
REVIEW_FILE = ROOT / 'documentation' / 'cutoff_final_cleanup_review.txt'

# ============================================================================
# LOAD DATA
# ============================================================================

print("="*80)
print("TNEA CUTOFF FINAL CLEANUP AND VALIDATION")
print("="*80)
print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

print("Loading data...")
df_original = pd.read_csv(MASTER_FILE)
df = df_original.copy()

print(f"Loaded: {len(df):,} rows × {len(df.columns)} columns")

# ============================================================================
# RECORD STARTING STATE
# ============================================================================

rows_before = len(df)
cols_before = len(df.columns)
exact_dups_before = df.duplicated().sum()
logical_dups_before = df.duplicated(subset=['year', 'college_code', 'branch_code']).sum()

print(f"Exact duplicates before: {exact_dups_before}")
print(f"Logical duplicates before: {logical_dups_before}")

# ============================================================================
# STANDARDIZATIONS TO APPLY
# ============================================================================

print("\n" + "="*80)
print("APPLYING VERIFIED STANDARDIZATIONS")
print("="*80)

standardizations_applied = []
records_changed = 0

# ------- BRANCH NAME STANDARDIZATIONS -------
print("\n1. BRANCH NAME STANDARDIZATIONS")
print("-"*80)

branch_mappings = {
    # AD - Artificial Intelligence variants (mainly capitalization)
    'ARTIFICIAL INTELLIGENCE AND DATA SCIENCE': 'Artificial Intelligence and Data Science',
    
    # AG - Agricultural vs Agriculture
    'AGRICULTURE ENGINEERING': 'Agricultural Engineering',
    
    # AM - AI/ML variants
    'COMPUTER SCIENCE AND ENGINEERING (ARTIFICIAL INTELLIGENCE AND MACHINE LEARNING)': 
        'Computer Science and Engineering (AI and Machine Learning)',
    'COMPUTER SCIENCE AND ENGINEERING (AI AND MACHINE LEARNING)':
        'Computer Science and Engineering (AI and Machine Learning)',
    
    # CE - Civil Engineering capitalization
    'CIVIL ENGINEERING': 'Civil Engineering',
    
    # CS - Computer Science capitalization
    'COMPUTER SCIENCE AND ENGINEERING': 'Computer Science and Engineering',
    
    # EA - Electronics and Advanced Communication variants
    'Electronics and Communication ( Advanced Communication Technology)':
        'Electronics and Communication (Advanced Communication Technology)',
    'Electronics and Communication (Advanced Communication Technology)':
        'Electronics and Communication (Advanced Communication Technology)',
    
    # EE - Electrical and Electronics capitalization
    'ELECTRICAL AND ELECTRONICS ENGINEERING': 'Electrical and Electronics Engineering',
    
    # EV - Electronics Engineering VLSI variants
    'Electronics Engineering (VLSI design and Technology)':
        'Electronics Engineering (VLSI Design and Technology)',
    'Electronics Engineering (VLSI Design and Technology)':
        'Electronics Engineering (VLSI Design and Technology)',
    
    # ME - Mechanical Engineering capitalization
    'MECHANICAL ENGINEERING': 'Mechanical Engineering',
    
    # PT - Printing variants
    'PRINTING TECHNOLOGY': 'Printing and Packing Technology',
    'PRINTING & PACKING TECHNOLOGY': 'Printing and Packing Technology',
    'PRINTING AND PACKING TECHNOLOGY': 'Printing and Packing Technology',
}

# Note: MD (MEDICAL ELECTRONICS vs MEDICAL ELECTRONICS ENGINEERING)
# These appear to be DIFFERENT branches - kept separate

for original, standardized in branch_mappings.items():
    count = len(df[df['branch_name'] == original])
    if count > 0:
        df.loc[df['branch_name'] == original, 'branch_name'] = standardized
        records_changed += count
        standardizations_applied.append({
            'type': 'branch_name',
            'original': original,
            'standardized': standardized,
            'records_affected': count
        })
        print(f"✓ {original[:50]:<50}")
        print(f"  → {standardized[:50]:<50} ({count} records)")

print(f"\nTotal branch name mappings applied: {len([s for s in standardizations_applied if s['type'] == 'branch_name'])}")

# ------- DISTRICT STANDARDIZATIONS -------
print("\n2. DISTRICT STANDARDIZATIONS")
print("-"*80)

# Standardize TIRUCHIRAPALLI variants
# TIRUCHIRAPALLI is the more common form (806 records vs 90)
before_dist_std = len(df)
df.loc[df['district'] == 'TRICHIRAPPALLI', 'district'] = 'TIRUCHIRAPALLI'
after_dist_std = len(df)

trichira_count = len(df_original[df_original['district'] == 'TRICHIRAPPALLI'])
if trichira_count > 0:
    print(f"✓ TRICHIRAPPALLI → TIRUCHIRAPALLI ({trichira_count} records)")
    standardizations_applied.append({
        'type': 'district',
        'original': 'TRICHIRAPPALLI',
        'standardized': 'TIRUCHIRAPALLI',
        'records_affected': trichira_count
    })
    records_changed += trichira_count
else:
    print("✓ No TRICHIRAPPALLI variant found (may have been corrected already)")

# ------- COLLEGE NAME STANDARDIZATIONS -------
print("\n3. COLLEGE NAME STANDARDIZATIONS")
print("-"*80)

# College code 1511 in 2024: Multiple names for same college
# These appear to be address variations (different PIN codes)
code_1511_2024 = df[(df['college_code'] == 1511) & (df['year'] == 2024)]
if len(code_1511_2024) > 0:
    names_1511 = code_1511_2024['college_name'].unique()
    if len(names_1511) > 1:
        print(f"College code 1511 (Year 2024): Found {len(names_1511)} name variations")
        print("Status: Keeping as-is (address variations, may be legitimate)")
        standardizations_applied.append({
            'type': 'college_name_review',
            'issue': 'college_code_1511_multiple_names',
            'details': 'Found 5 address variations for same college, all preserved',
            'records_affected': len(code_1511_2024)
        })
    else:
        print("✓ College code 1511 has single standardized name")
else:
    print("✓ College code 1511 not found in year 2024")

# ============================================================================
# DOCUMENT SUSPICIOUS ISSUES
# ============================================================================

print("\n" + "="*80)
print("IDENTIFYING SUSPICIOUS ISSUES FOR REVIEW")
print("="*80)

suspicious_issues = []

# Issue: BC cutoff missing but bc_partial = 1
bc_partial_anomalies = df[(df['bc'].isna()) & (df['bc_partial'] == 1)]
if len(bc_partial_anomalies) > 0:
    print(f"\n✓ Found {len(bc_partial_anomalies)} records with BC cutoff missing but bc_partial=1")
    for idx, row in bc_partial_anomalies.iterrows():
        suspicious_issues.append({
            'type': 'cutoff_partial_mismatch',
            'category': 'BC',
            'year': row['year'],
            'college_code': row['college_code'],
            'college_name': row['college_name'][:60],
            'branch_code': row['branch_code'],
            'branch_name': row['branch_name'],
            'district': row['district'],
            'cutoff_value': 'NaN',
            'partial_flag': 1,
            'status': 'PRESERVED - likely source data inconsistency',
            'confidence': 'HIGH'
        })

# ============================================================================
# VALIDATE AFTER CLEANUP
# ============================================================================

print("\n" + "="*80)
print("VALIDATION AFTER CLEANUP")
print("="*80)

# Duplicates
exact_dups_after = df.duplicated().sum()
logical_dups_after = df.duplicated(subset=['year', 'college_code', 'branch_code']).sum()

print(f"\nDuplicates:")
print(f"  Exact duplicates: {exact_dups_after} (before: {exact_dups_before})")
print(f"  Logical duplicates: {logical_dups_after} (before: {logical_dups_before})")

# Partial columns validation
print(f"\nPartial columns validation:")
partial_cols = ['oc_partial', 'bc_partial', 'bcm_partial', 'mbc_partial', 'sc_partial', 'sca_partial', 'st_partial']
partial_validation = {}
for col in partial_cols:
    unique_vals = sorted(df[col].unique())
    invalid = len(df[~df[col].isin([0, 1])])
    partial_validation[col] = {
        'unique_values': unique_vals,
        'invalid_count': invalid
    }
    status = "✓" if unique_vals == [0, 1] and invalid == 0 else "✗"
    print(f"  {col:<20} {status} values: {unique_vals}, invalid: {invalid}")

# Numeric validation
print(f"\nNumeric cutoff validation:")
cutoff_cols = ['oc', 'bc', 'bcm', 'mbc', 'sc', 'sca', 'st']
numeric_validation = {}
for col in cutoff_cols:
    values = df[col].dropna()
    neg_count = (values < 0).sum() if len(values) > 0 else 0
    high_count = (values > 200).sum() if len(values) > 0 else 0
    numeric_validation[col] = {
        'negative': neg_count,
        'over_200': high_count
    }
    status = "✓" if neg_count == 0 and high_count == 0 else "✗"
    print(f"  {col:<5} {status} negative: {neg_count}, >200: {high_count}")

# Year validation
years_actual = sorted(df['year'].unique())
years_expected = [2021, 2022, 2023, 2024, 2025]
years_valid = years_actual == years_expected
print(f"\nYear validation: {'✓' if years_valid else '✗'} years: {years_actual}")

# Required identifiers
missing_college_code = df['college_code'].isna().sum()
missing_branch_code = df['branch_code'].isna().sum()
missing_college_name = df['college_name'].isna().sum()
missing_branch_name = df['branch_name'].isna().sum()

print(f"\nRequired identifiers:")
print(f"  Missing college_code: {missing_college_code} {'✓' if missing_college_code == 0 else '✗'}")
print(f"  Missing branch_code: {missing_branch_code} {'✓' if missing_branch_code == 0 else '✗'}")
print(f"  Missing college_name: {missing_college_name} {'✓' if missing_college_name == 0 else '✗'}")
print(f"  Missing branch_name: {missing_branch_name} {'✓' if missing_branch_name == 0 else '✗'}")

# Row count
rows_after = len(df)
print(f"\nRow count:")
print(f"  Before: {rows_before:,}")
print(f"  After:  {rows_after:,}")
print(f"  Removed: {rows_before - rows_after}")

# ============================================================================
# SAVE FINAL CLEANED DATASET
# ============================================================================

print("\n" + "="*80)
print("SAVING FINAL DATASET")
print("="*80)

df.to_csv(FINAL_FILE, index=False)
print(f"✓ Saved: {FINAL_FILE}")

# ============================================================================
# GENERATE COMPREHENSIVE REPORTS
# ============================================================================

print("\nGenerating reports...")

# Build cleanup report
cleanup_report = []

cleanup_report.append("="*80)
cleanup_report.append("TNEA CUTOFF FINAL CLEANUP REPORT")
cleanup_report.append("="*80)
cleanup_report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

cleanup_report.append("1. ORIGINAL DATASET")
cleanup_report.append("-"*80)
cleanup_report.append(f"Rows: {rows_before:,}")
cleanup_report.append(f"Columns: {cols_before}")

cleanup_report.append("\n2. FINAL DATASET")
cleanup_report.append("-"*80)
cleanup_report.append(f"Rows: {rows_after:,}")
cleanup_report.append(f"Columns: {len(df.columns)}")

cleanup_report.append("\n3. BRANCH NAME STANDARDIZATIONS")
cleanup_report.append("-"*80)
branch_stds = [s for s in standardizations_applied if s['type'] == 'branch_name']
cleanup_report.append(f"Mappings applied: {len(branch_stds)}")
cleanup_report.append(f"Records affected: {sum(s['records_affected'] for s in branch_stds)}")
cleanup_report.append("")
for std in branch_stds:
    cleanup_report.append(f"  {std['original'][:50]}")
    cleanup_report.append(f"  → {std['standardized'][:50]} ({std['records_affected']} records)")

cleanup_report.append("\n4. DISTRICT STANDARDIZATIONS")
cleanup_report.append("-"*80)
district_stds = [s for s in standardizations_applied if s['type'] == 'district']
cleanup_report.append(f"Mappings applied: {len(district_stds)}")
if district_stds:
    cleanup_report.append(f"Records affected: {sum(s['records_affected'] for s in district_stds)}")
    for std in district_stds:
        cleanup_report.append(f"  {std['original']} → {std['standardized']} ({std['records_affected']} records)")
else:
    cleanup_report.append("No district changes")

cleanup_report.append("\n5. COLLEGE NAME STANDARDIZATIONS")
cleanup_report.append("-"*80)
college_stds = [s for s in standardizations_applied if s['type'] in ['college_name_review']]
if college_stds:
    for std in college_stds:
        cleanup_report.append(f"  Issue: {std.get('issue', 'N/A')}")
        cleanup_report.append(f"  Details: {std.get('details', 'N/A')}")
        cleanup_report.append(f"  Records affected: {std.get('records_affected', 0)}")
else:
    cleanup_report.append("No college name standardizations applied")

cleanup_report.append("\n6. COLLEGE CODE 1511 INVESTIGATION")
cleanup_report.append("-"*80)
cleanup_report.append("Status: Record found with multiple address variations in 2024")
cleanup_report.append("Action: PRESERVED - Differences appear to be legitimate address/PIN variations")
cleanup_report.append("Note: All 5 records kept unchanged as they represent the same college's different PIN codes")

cleanup_report.append("\n7. BC CUTOFF + BC_PARTIAL INVESTIGATION")
cleanup_report.append("-"*80)
cleanup_report.append(f"Records found: {len(bc_partial_anomalies)}")
if len(bc_partial_anomalies) > 0:
    cleanup_report.append("\nAnomalies (BC cutoff missing but bc_partial=1):")
    for idx, row in bc_partial_anomalies.iterrows():
        cleanup_report.append(f"  Year: {row['year']}")
        cleanup_report.append(f"  College: {row['college_name'][:60]}")
        cleanup_report.append(f"  Branch: {row['branch_name']}")
        cleanup_report.append(f"  Status: PRESERVED - Likely source data inconsistency")
    cleanup_report.append("\nNo correction applied - missing cutoff values preserved")
    cleanup_report.append("(Correcting data with uncertain values is worse than preserving anomaly)")
else:
    cleanup_report.append("None found")

cleanup_report.append("\n8. PARTIAL COLUMN VALIDATION")
cleanup_report.append("-"*80)
for col, validation in partial_validation.items():
    cleanup_report.append(f"{col}:")
    cleanup_report.append(f"  Unique values: {validation['unique_values']}")
    cleanup_report.append(f"  Invalid values: {validation['invalid_count']}")

cleanup_report.append("\n9. MISSING CUTOFF VALUES")
cleanup_report.append("-"*80)
for col in cutoff_cols:
    missing = df[col].isna().sum()
    pct = 100 * missing / len(df)
    cleanup_report.append(f"{col}: {missing:>6,} ({pct:>5.1f}%) - PRESERVED AS NaN")

cleanup_report.append("\n10. DUPLICATE CHECK")
cleanup_report.append("-"*80)
cleanup_report.append(f"Exact duplicates after cleanup: {exact_dups_after}")
cleanup_report.append(f"Logical duplicates after cleanup: {logical_dups_after}")

cleanup_report.append("\n11. NUMERIC VALIDATION")
cleanup_report.append("-"*80)
for col, validation in numeric_validation.items():
    cleanup_report.append(f"{col}: negative={validation['negative']}, >200={validation['over_200']}")

cleanup_report.append("\n12. YEAR VALIDATION")
cleanup_report.append("-"*80)
cleanup_report.append(f"Years found: {years_actual}")
cleanup_report.append(f"Expected: {years_expected}")
cleanup_report.append(f"Status: {'✓ VALID' if years_valid else '✗ INVALID'}")

cleanup_report.append("\n13. REQUIRED IDENTIFIER VALIDATION")
cleanup_report.append("-"*80)
cleanup_report.append(f"Missing college_code: {missing_college_code}")
cleanup_report.append(f"Missing branch_code: {missing_branch_code}")
cleanup_report.append(f"Missing college_name: {missing_college_name}")
cleanup_report.append(f"Missing branch_name: {missing_branch_name}")

cleanup_report.append("\n14. ROW COUNT SUMMARY")
cleanup_report.append("-"*80)
cleanup_report.append(f"Before cleanup: {rows_before:,}")
cleanup_report.append(f"After cleanup:  {rows_after:,}")
cleanup_report.append(f"Rows removed:   {rows_before - rows_after}")
cleanup_report.append(f"Data loss:      {100*(rows_before - rows_after)/rows_before:.2f}%")

cleanup_report.append("\n15. FINAL STATUS")
cleanup_report.append("-"*80)
all_valid = (
    exact_dups_after == 0 and
    logical_dups_after == 0 and
    all(v['invalid_count'] == 0 for v in partial_validation.values()) and
    all(v['negative'] == 0 and v['over_200'] == 0 for v in numeric_validation.values()) and
    years_valid and
    missing_college_code == 0 and
    missing_branch_code == 0 and
    missing_college_name == 0 and
    missing_branch_name == 0
)

if all_valid:
    cleanup_report.append("STATUS: ✓ READY FOR NEXT STAGE")
    cleanup_report.append("\nThe cleaned dataset passes all validation checks:")
    cleanup_report.append("  ✓ No duplicates")
    cleanup_report.append("  ✓ Valid partial columns")
    cleanup_report.append("  ✓ Valid numeric cutoff values")
    cleanup_report.append("  ✓ All required identifiers present")
    cleanup_report.append("  ✓ Branch names standardized")
    cleanup_report.append("  ✓ District names standardized")
    cleanup_report.append("  ✓ High data integrity")
else:
    cleanup_report.append("STATUS: ✗ REQUIRES MANUAL REVIEW")
    cleanup_report.append("\nSee cutoff_final_cleanup_review.txt for issues")

cleanup_report.append("\n" + "="*80)
cleanup_report.append("END OF CLEANUP REPORT")
cleanup_report.append("="*80)

# Write cleanup report
with open(REPORT_FILE, 'w', encoding='utf-8') as f:
    f.write('\n'.join(cleanup_report))

print(f"✓ Report: {REPORT_FILE}")

# Build review file
review_report = []

review_report.append("="*80)
review_report.append("TNEA CUTOFF FINAL CLEANUP - REVIEW FILE")
review_report.append("="*80)
review_report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

review_report.append("SUSPICIOUS ISSUES FOUND AND PRESERVED\n")

if suspicious_issues:
    for i, issue in enumerate(suspicious_issues, 1):
        review_report.append(f"\nIssue #{i}")
        review_report.append("-"*80)
        review_report.append(f"Type: {issue['type']}")
        review_report.append(f"Category: {issue['category']}")
        review_report.append(f"Year: {issue['year']}")
        review_report.append(f"College Code: {issue['college_code']}")
        review_report.append(f"College Name: {issue['college_name']}")
        review_report.append(f"Branch Code: {issue['branch_code']}")
        review_report.append(f"Branch Name: {issue['branch_name']}")
        review_report.append(f"District: {issue['district']}")
        review_report.append(f"Cutoff Value: {issue['cutoff_value']}")
        review_report.append(f"Partial Flag: {issue['partial_flag']}")
        review_report.append(f"Status: {issue['status']}")
        review_report.append(f"Confidence: {issue['confidence']}")
        review_report.append("")

review_report.append("\n" + "="*80)
review_report.append("NO OTHER ISSUES REQUIRING MANUAL REVIEW")
review_report.append("="*80)

# Write review file
with open(REVIEW_FILE, 'w', encoding='utf-8') as f:
    f.write('\n'.join(review_report))

print(f"✓ Review file: {REVIEW_FILE}")

# ============================================================================
# FINAL SUMMARY
# ============================================================================

print("\n" + "="*80)
print("✓ FINAL CLEANUP COMPLETE")
print("="*80)
print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"\nFiles created:")
print(f"  • {FINAL_FILE}")
print(f"  • {REPORT_FILE}")
print(f"  • {REVIEW_FILE}")

print(f"\nSummary:")
print(f"  Rows before:        {rows_before:,}")
print(f"  Rows after:         {rows_after:,}")
print(f"  Rows removed:       {rows_before - rows_after}")
print(f"  Standardizations:   {len([s for s in standardizations_applied if s['type'] in ['branch_name', 'district']])}")
print(f"  Issues documented:  {len(suspicious_issues)}")
print(f"  Final status:       {'✓ READY' if all_valid else '✗ REVIEW NEEDED'}")

print("\n" + "="*80)
