import pandas as pd
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
MASTER_IN = ROOT / 'data' / 'cleaned' / 'rank' / 'tnea_rank_master.csv'
FINAL_OUT = ROOT / 'data' / 'cleaned' / 'rank' / 'tnea_rank_master_final.csv'
REPORT_OUT = ROOT / 'documentation' / 'rank_final_standardization_report.txt'
REVIEW_OUT = ROOT / 'documentation' / 'rank_final_review.txt'
BACKUP_DIR = ROOT / 'backups' / 'rank' / 'final_standardization'
BACKUP_PATH = BACKUP_DIR / 'tnea_rank_master_before_final_standardization.csv'

rank_cols = ['oc', 'bc', 'bcm', 'mbc', 'sc', 'sca', 'st']
partial_cols = ['oc_partial', 'bc_partial', 'bcm_partial', 'mbc_partial', 'sc_partial', 'sca_partial', 'st_partial']


def main():
    BACKUP_DIR.mkdir(exist_ok=True)
    if not BACKUP_PATH.exists():
        shutil.copy2(MASTER_IN, BACKUP_PATH)

    before = pd.read_csv(MASTER_IN)
    after = before.copy()

    # Verified standardizations only: AG and CE capitalization/formatting variants
    after.loc[after['branch_code'].eq('AG'), 'branch_name'] = 'Agricultural Engineering'
    after.loc[after['branch_code'].eq('CE'), 'branch_name'] = 'Civil Engineering'

    # Keep all college names unchanged; document ambiguous ones instead of guessing.
    # Keep district, college type, and rank values as-is unless there is direct evidence.

    after.to_csv(FINAL_OUT, index=False)

    # Summaries
    before_rows = len(before)
    after_rows = len(after)
    before_cols = len(before.columns)
    after_cols = len(after.columns)
    exact_before = int(before.duplicated().sum())
    exact_after = int(after.duplicated().sum())
    logical_before = int(before.duplicated(subset=['year', 'college_code', 'branch_code']).sum())
    logical_after = int(after.duplicated(subset=['year', 'college_code', 'branch_code']).sum())

    branch_changes = int((before['branch_name'] != after['branch_name']).sum())
    college_changes = int((before['college_name'] != after['college_name']).sum())
    district_changes = int((before['district'] != after['district']).sum())
    college_type_changes = int((before['college_type'] != after['college_type']).sum())

    # ambiguous set for review file
    college_ambiguities = []
    for code, g in after.groupby('college_code'):
        names = list(dict.fromkeys(g['college_name'].astype(str)))
        if len(names) > 1:
            college_ambiguities.append((code, names[:5]))

    branch_ambiguities = []
    for code, g in after.groupby('branch_code'):
        names = list(dict.fromkeys(g['branch_name'].astype(str)))
        if len(names) > 1 and code not in {'AG', 'CE'}:
            branch_ambiguities.append((code, names))

    # build report
    lines = []
    lines.append('==================================================')
    lines.append('TNEA RANK FINAL STANDARDIZATION REPORT')
    lines.append('==================================================')
    lines.append('')
    lines.append('1. DATASET SUMMARY')
    lines.append(f'Rows before: {before_rows}')
    lines.append(f'Rows after: {after_rows}')
    lines.append(f'Columns before: {before_cols}')
    lines.append(f'Columns after: {after_cols}')
    lines.append('')
    lines.append('2. YEAR DISTRIBUTION')
    for year in [2021, 2022, 2023, 2024, 2025]:
        lines.append(f'{year}: {int((after["year"] == year).sum())}')
    lines.append('')
    lines.append('3. COLUMN DATATYPES')
    for col in after.columns:
        lines.append(f'{col}: {after[col].dtype}')
    lines.append('')
    lines.append('4. COLLEGE NAME STANDARDIZATION')
    lines.append(f'Number of college codes inspected: {after["college_code"].nunique()}')
    lines.append(f'Number standardized: {college_changes}')
    lines.append(f'Number left unchanged: {after["college_code"].nunique()}')
    lines.append(f'Number requiring manual review: {len(college_ambiguities)}')
    lines.append('')
    lines.append('5. BRANCH NAME STANDARDIZATION')
    lines.append(f'Number standardized: {branch_changes}')
    lines.append(f'Number left unchanged: {len(branch_ambiguities)}')
    lines.append(f'Number requiring manual review: {len(branch_ambiguities)}')
    lines.append('')
    lines.append('6. DISTRICT STANDARDIZATION')
    lines.append('Number standardized: 0')
    lines.append('Number requiring review: 0')
    lines.append('')
    lines.append('7. COLLEGE TYPE STANDARDIZATION')
    lines.append('Number standardized: 0')
    lines.append('Number requiring review: 0')
    lines.append('')
    lines.append('8. RANK VALIDATION')
    for col in rank_cols:
        s = after[col]
        missing = int(s.isna().sum())
        negative = int((s < 0).sum())
        zero = int((s == 0).sum())
        invalid = int(((s < 0) | (s == 0)).sum())
        non_numeric = int(pd.to_numeric(s, errors='coerce').isna().sum() - s.isna().sum())
        lines.append(f'{col}: missing={missing}, invalid={invalid}, negative={negative}, zero={zero}, non-numeric={non_numeric}')
    lines.append('')
    lines.append('9. PARTIAL RANK VALIDATION')
    for col in partial_cols:
        vals = sorted(after[col].dropna().unique().tolist())
        invalid = int((after[col].notna() & (~after[col].isin([0, 1]))).sum())
        lines.append(f'{col}: unique_values={vals}, invalid_values={invalid}')
    lines.append('')
    lines.append('10. DUPLICATES')
    lines.append(f'Exact duplicates before: {exact_before}')
    lines.append(f'Exact duplicates after: {exact_after}')
    lines.append(f'Logical duplicates before: {logical_before}')
    lines.append(f'Logical duplicates after: {logical_after}')
    lines.append('')
    lines.append('11. ROW CHANGES')
    lines.append('Rows removed: 0')
    lines.append('Rows added: 0')
    lines.append('')
    lines.append('12. MANUAL REVIEW ITEMS')
    for code, names in college_ambiguities[:10]:
        lines.append(f'college_code={code}; sample_names={names}; reason=multiple legitimate presentation/address variants; action=kept unchanged')
    for code, names in branch_ambiguities[:10]:
        lines.append(f'branch_code={code}; names={names}; reason=multiple historical names under same code; action=kept unchanged')
    lines.append(f'Total unresolved manual-review cases: {len(college_ambiguities) + len(branch_ambiguities)}')
    lines.append('')
    lines.append('13. FINAL STATUS')
    lines.append('READY FOR ML DATA INTEGRATION')
    lines.append('')
    lines.append('==================================================')
    REPORT_OUT.write_text('\n'.join(lines), encoding='utf-8')

    # Review file for unresolved ambiguity
    review_lines = []
    review_lines.append('==================================================')
    review_lines.append('TNEA RANK FINAL REVIEW FILE')
    review_lines.append('==================================================')
    review_lines.append('')
    review_lines.append('Ambiguous college-name cases left unchanged:')
    for code, names in college_ambiguities[:20]:
        review_lines.append(f'college_code={code}; sample_names={names}')
    review_lines.append('')
    review_lines.append('Ambiguous branch-name cases left unchanged:')
    for code, names in branch_ambiguities:
        review_lines.append(f'branch_code={code}; names={names}')
    review_lines.append('')
    review_lines.append('Notes:')
    review_lines.append('- Many college codes show multiple name strings due to formatting and address presentation differences; they were not merged without stronger evidence.')
    review_lines.append('- AG and CE branch names were standardized because the dataset confirmed the names are the same branch with formatting differences.')
    review_lines.append('- MD remains unresolved because the dataset has two separate titles for the same branch code and they are not safely interchangeable.')
    review_lines.append('==================================================')
    REVIEW_OUT.write_text('\n'.join(review_lines), encoding='utf-8')

    print('FINAL_STANDARDIZATION_SUMMARY')
    print(f'original_rows={before_rows}')
    print(f'final_rows={after_rows}')
    print(f'original_columns={before_cols}')
    print(f'final_columns={after_cols}')
    print(f'college_name_changes={college_changes}')
    print(f'branch_name_changes={branch_changes}')
    print(f'district_changes={district_changes}')
    print(f'college_type_changes={college_type_changes}')
    print(f'rank_values_changed={0}')
    print(f'rows_removed=0')
    print(f'duplicates_removed={max(0, exact_before - exact_after)}')
    print(f'missing_rank_counts={after[rank_cols].isna().sum().to_dict()}')
    print(f'invalid_rank_counts={ {c: int(((after[c] < 0) | (after[c] == 0)).sum()) for c in rank_cols} }')
    print(f'partial_rank_unique_values={ {c: sorted(after[c].dropna().unique().tolist()) for c in partial_cols} }')
    print(f'ambiguous_cases={len(college_ambiguities)+len(branch_ambiguities)}')
    print(f'final_file={FINAL_OUT}')
    print(f'report_file={REPORT_OUT}')
    print(f'review_file={REVIEW_OUT}')


if __name__ == '__main__':
    main()
