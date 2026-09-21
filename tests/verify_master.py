from pathlib import Path

import pandas as pd

master = pd.read_csv(Path(__file__).resolve().parents[1] / 'data' / 'cleaned' / 'cutoff' / 'tnea_cutoff_master.csv')

print('MASTER DATASET SUMMARY')
print('='*70)
print(f'Total rows: {len(master):,}')
print(f'Total columns: {len(master.columns)}')
print(f'Year range: {master["year"].min()}-{master["year"].max()}')
print(f'Unique colleges: {master["college_code"].nunique()}')
print(f'Unique branches: {master["branch_code"].nunique()}')
print(f'\nRows per year:')
print(master['year'].value_counts().sort_index().to_string())
print(f'\nMemory usage: {master.memory_usage(deep=True).sum()/1024/1024:.2f} MB')
print(f'\nMissing values per cutoff column:')
print(master[['oc', 'bc', 'bcm', 'mbc', 'sc', 'sca', 'st']].isna().sum().to_string())
