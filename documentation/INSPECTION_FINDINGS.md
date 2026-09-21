======================================================================
TNEA CUTOFF DATA INSPECTION REPORT
======================================================================

YEAR SUMMARY
----------------------------------------------------------------------

2021:
  Raw rows:        2830
  Columns:         20
  Exact duplicates: 0
  Logical duplicates (college+branch): 0
  Unique colleges: 440
  Unique branches: 98

2022:
  Raw rows:        3089
  Columns:         20
  Exact duplicates: 0
  Logical duplicates (college+branch): 0
  Unique colleges: 446
  Unique branches: 100

2023:
  Raw rows:        3324
  Columns:         20
  Exact duplicates: 0
  Logical duplicates (college+branch): 0
  Unique colleges: 440
  Unique branches: 100

2024:
  Raw rows:        3474
  Columns:         20
  Exact duplicates: 0
  Logical duplicates (college+branch): 0
  Unique colleges: 434
  Unique branches: 106

2025:
  Raw rows:        3457
  Columns:         20
  Exact duplicates: 0
  Logical duplicates (college+branch): 0
  Unique colleges: 423
  Unique branches: 106

CRITICAL FINDINGS
======================================================================

✓ GOOD NEWS:
  - All 5 years have IDENTICAL column structure (20 columns, same names)
  - NO exact duplicate rows detected in any year
  - NO logical duplicates (college_code + branch_code pairs are unique)
  - All cutoff values are already numeric (float64)
  - Partial cutoff columns are all integers (0/1 flags)
  - No negative cutoff values
  - No impossible/extreme values (all within reasonable range)
  - College names and district names are clean (no empty values)

⚠ ISSUES REQUIRING ATTENTION:

1. INCONSISTENT COLLEGE NAME FORMATTING:
   - 2021-2022: College names use quoted format with full addresses
   - 2023-2025: College names use different format (no quotes, missing commas)
   
   Example:
   2021: "University Departments of Anna University, Chennai - CEG Campus..."
   2023: University Departments of Anna University  Chennai - CEG Campus...
   
   ACTION: Standardize formatting when cleaning

2. MISSING CUTOFF VALUES (Strategic Absences, NOT errors):
   
   a) OC (Open Category):
      2021: 260 missing, 2570 valid
      2022: 339 missing, 2750 valid
      2023: 285 missing, 3039 valid
      2024: 286 missing, 3188 valid
      2025: 155 missing, 3302 valid
      
      REASON: Likely courses not offered in OC category
      ACTION: Keep as missing (NaN), don't replace with 0
   
   b) BC, BCM, MBC, SC (Backward Class Categories):
      Similar pattern - missing where category not offered
      Values range: 77.50 to 200.00 (reasonable)
      
   c) SCA, ST (Scheduled Caste/Tribe Special):
      Highest missing rates (60-70% missing)
      These are special categories with limited availability
      ACTION: Keep as missing (NaN)
      
   d) ST (Scheduled Tribe):
      Very high missing rate (73-88%)
      Valid values range: 78.00 to 197.00
      ACTION: Keep as missing (NaN)

3. VARYING NUMBER OF COLLEGES & BRANCHES:
   
   Colleges:
   2021: 440 | 2022: 446 | 2023: 440 | 2024: 434 | 2025: 423
   
   Branches:
   2021: 98 | 2022: 100 | 2023: 100 | 2024: 106 | 2025: 106
   
   REASON: College programs change year to year (new branches added, others removed)
   ACTION: This is NORMAL and expected. Keep all variations.

4. DISTRICT DISTRIBUTION:
   - 39 unique districts in all years (consistent)
   - No empty district values
   - Districts appear properly formatted (e.g., CHENNAI, COIMBATORE, VELLORE)

5. COLLEGE TYPE DISTRIBUTION:
   - 9 unique types across all years
   - Examples: CEG DEPTS, GOVERNMENT ENGG COLLEGES, PRIVATE ENGG COLLEGES
   - No empty values
   - Consistent across years

COLUMN STRUCTURE DETAIL
======================================================================

All 20 columns (identical across all years):

1. college_code (int64):
   - Numeric identifiers (1, 2, 1013, 1014, etc.)
   - Range: 1 to ~2000+
   - No duplicates within a year
   
2. college_name (str):
   - Full college names with addresses
   - 440-446 unique values per year
   - Formatting inconsistency noted (see issue #1)
   
3. district (str):
   - Tamil Nadu district names
   - 39 unique values (same across all years)
   - All uppercase format
   
4. college_type (str):
   - 9 unique types (same across all years)
   - Includes CEG DEPTS, Government colleges, Private colleges, etc.
   
5. branch_code (str):
   - Two-letter codes (CS, CE, EC, ME, EE, etc.)
   - 98-106 unique values per year
   - No duplicates within year+college combo
   
6. branch_name (str):
   - Full branch names (Computer Science, Civil Engineering, etc.)
   - 98-110 unique values per year
   - Some variation in naming convention year to year
   
7-13. oc, bc, bcm, mbc, sc, sca, st (float64):
   - Main cutoff score columns
   - Range: ~77.50 to 200.00
   - Many missing values (strategic, not errors)
   - All numeric already, properly formatted
   
14-20. oc_partial, bc_partial, ... st_partial (int64):
   - Boolean flags (0 or 1)
   - Indicate whether partial scores exist
   - All 0 in visible data (partial admissions flag)

DATA QUALITY SUMMARY
======================================================================

                     2021    2022    2023    2024    2025
─────────────────────────────────────────────────────────
Total Rows:          2830    3089    3324    3474    3457
Unique Colleges:      440     446     440     434     423
Unique Branches:       98     100     100     106     106
Exact Duplicates:        0       0       0       0       0
Logical Duplicates:      0       0       0       0       0

Cutoff Columns Coverage (%):
  OC:                 90.8%   89.0%   91.4%   91.8%   95.5%
  BC:                 61.7%   63.5%   65.6%   65.6%   76.5%
  BCM:                46.3%   44.5%   47.0%   46.3%   58.1%
  MBC:                45.3%   61.5%   64.5%   65.2%   76.0%
  SC:                 57.3%   57.4%   58.3%   59.4%   72.2%
  SCA:                28.1%   26.2%   28.0%   30.8%   38.6%
  ST:                   8.8%    8.2%    8.9%   11.1%   14.4%

Cutoff Value Ranges (All Valid Values):
  OC:   77.50  -  200.00  (Mean: 131-155)
  BC:   78.00  -  200.00  (Mean: 121-155)
  BCM:  77.50  -  199.50  (Mean: 135-162)
  MBC:  77.50  -  200.00  (Mean: 122-165)
  SC:   77.50  -  198.50  (Mean: 108-120)
  SCA:  77.50  -  197.50  (Mean: 118-152)
  ST:   78.00  -  197.00  (Mean: 126-153)

RECOMMENDATIONS FOR CLEANING
======================================================================

✓ KEEP AS-IS:
  - All 20 columns (all are useful)
  - All rows (no genuine errors to remove)
  - All colleges and branches (variation is legitimate)
  - All missing values as NaN (missing ≠ zero)
  - All numeric cutoff values (already properly formatted)
  - All text fields (well-formatted, no corruption)

⚠ NEEDS STANDARDIZATION:
  1. College name formatting (commas/hyphens in 2023-2025 differ from 2021-2022)
  2. Column names: Keep lowercase, no spaces (already good)
  3. Text field whitespace: Trim leading/trailing spaces
  4. Add 'year' column to each dataset for identification

✗ NO NEED TO:
  - Replace missing values with 0 (they mean "not applicable")
  - Remove colleges/branches (legitimate variation)
  - Remove low values (all are valid cutoffs)
  - Aggregate or merge data (keep granular)

NEXT STEPS (CLEANING PHASE)
======================================================================

1. Standardize college_name formatting (handle 2023-2025 format differences)
2. Trim whitespace from text columns
3. Add 'year' column to each dataset
4. Reorder columns logically: year, college_code, college_name, district, college_type, branch_code, branch_name, then cutoffs
5. Sort by: college_code, branch_code
6. Create cleaned yearly files in cleaned_cutoff_data/
7. Merge all years into master dataset
8. Generate detailed validation report

======================================================================
END OF INSPECTION REPORT
Generated: Before cleaning phase
======================================================================
