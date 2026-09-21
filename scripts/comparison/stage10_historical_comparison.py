from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = ROOT / "data" / "integrated" / "tnea_integrated_master.csv"
REPORT_PATH = ROOT / "documentation" / "historical_comparison_report.txt"
KEY_COLUMNS = ["year", "college_code", "branch_code"]
CATEGORIES = ["OC", "BC", "BCM", "MBC", "SC", "SCA", "ST"]
CATEGORY_COLUMNS = {
    "OC": {"cutoff": "cutoff_oc", "rank": "rank_oc"},
    "BC": {"cutoff": "cutoff_bc", "rank": "rank_bc"},
    "BCM": {"cutoff": "cutoff_bcm", "rank": "rank_bcm"},
    "MBC": {"cutoff": "cutoff_mbc", "rank": "rank_mbc"},
    "SC": {"cutoff": "cutoff_sc", "rank": "rank_sc"},
    "SCA": {"cutoff": "cutoff_sca", "rank": "rank_sca"},
    "ST": {"cutoff": "cutoff_st", "rank": "rank_st"},
}
IDENTIFIER_COLUMNS = [
    "year",
    "college_code",
    "college_name",
    "district",
    "college_type",
    "branch_code",
    "branch_name",
]
PARTIAL_COLUMNS = [
    f"{measure}_{category.lower()}_partial"
    for measure in ("cutoff", "rank")
    for category in CATEGORIES
]
REQUIRED_COLUMNS = IDENTIFIER_COLUMNS + [
    column
    for mapping in CATEGORY_COLUMNS.values()
    for column in mapping.values()
] + PARTIAL_COLUMNS


WORKING_ASSUMPTIONS = {
    "cutoff": "student cutoff >= historical cutoff",
    "rank": "student rank <= historical rank",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_years(value: str) -> list[int]:
    try:
        years = sorted({int(item.strip()) for item in value.split(",") if item.strip()})
    except ValueError as error:
        raise ValueError("years must be comma-separated integers") from error
    if not years:
        raise ValueError("at least one historical year is required")
    return years


def validate_frame(frame: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"input is missing required columns: {missing}")
    duplicate_keys = int(frame.duplicated(KEY_COLUMNS).sum())
    if duplicate_keys:
        raise ValueError(f"input contains {duplicate_keys} duplicate primary-key rows")


def validate_inputs(
    frame: pd.DataFrame,
    district: str | None,
    branch_code: str | None,
    category: str | None,
    input_type: str | None,
    student_value: float | None,
    years: list[int] | None,
) -> None:
    if not district or not district.strip():
        raise ValueError("district is required")
    if not branch_code or not branch_code.strip():
        raise ValueError("exact branch_code is required")
    if category not in CATEGORIES:
        raise ValueError(f"invalid category {category!r}; expected one of {CATEGORIES}")
    if input_type not in {"cutoff", "rank"}:
        raise ValueError("input_type must be cutoff or rank")
    if student_value is None:
        raise ValueError("student_value is required")
    if student_value <= 0:
        raise ValueError("student_value must be greater than zero")
    available_years = set(int(value) for value in frame["year"].unique())
    unknown_years = sorted(set(years or []) - available_years)
    if unknown_years:
        raise ValueError(f"invalid year(s) not present in dataset: {unknown_years}")


def comparison_results(
    frame: pd.DataFrame,
    district: str,
    branch_code: str,
    category: str,
    input_type: str,
    student_value: float,
    years: list[int],
) -> pd.DataFrame:
    district_key = district.strip().casefold()
    branch_key = branch_code.strip().casefold()
    selected = frame[
        frame["district"].astype(str).str.strip().str.casefold().eq(district_key)
        & frame["branch_code"].astype(str).str.strip().str.casefold().eq(branch_key)
        & frame["year"].isin(years)
    ].copy()
    value_column = CATEGORY_COLUMNS[category][input_type]
    rows: list[dict[str, object]] = []
    group_columns = ["college_code", "branch_code"]
    for identity, group in selected.groupby(group_columns, dropna=False):
        college_names = sorted(group["college_name"].dropna().astype(str).unique().tolist())
        districts = sorted(group["district"].dropna().astype(str).unique().tolist())
        branch_names = sorted(group["branch_name"].dropna().astype(str).unique().tolist())
        values = pd.to_numeric(group[value_column], errors="coerce")
        by_year = {
            int(year): (None if pd.isna(value) else float(value))
            for year, value in zip(group["year"], group[value_column])
        }
        usable_years = sorted(int(year) for year, value in by_year.items() if value is not None)
        missing_years = sorted(set(years) - set(usable_years))
        if input_type == "cutoff":
            meets_by_year = {
                year: (None if value is None else student_value >= value)
                for year, value in by_year.items()
            }
        else:
            meets_by_year = {
                year: (None if value is None else student_value <= value)
                for year, value in by_year.items()
            }
        years_meeting = sum(value is True for value in meets_by_year.values())
        rate = years_meeting / len(usable_years) if usable_years else None
        if not usable_years:
            status = "No comparable records"
        elif len(usable_years) == 1:
            status = "Insufficient historical data"
        elif years_meeting == len(usable_years):
            status = "Historical threshold matched in all usable years"
        elif years_meeting:
            status = "Historical threshold matched in some years"
        else:
            status = "Historical threshold not matched in usable years"
        rows.append(
            {
                "college_code": identity[0],
                "college_name": college_names[0] if college_names else "",
                "district": districts[0] if districts else "",
                "branch_code": identity[1],
                "branch_name": branch_names[0] if branch_names else "",
                "observed_college_names": college_names,
                "observed_districts": districts,
                "observed_branch_names": branch_names,
                "category": category,
                "input_type": input_type,
                "student_value": student_value,
                "requested_years": ",".join(str(year) for year in years),
                "historical_values_by_year": by_year,
                "meets_threshold_by_year": meets_by_year,
                "usable_years": usable_years,
                "missing_years": missing_years,
                "years_meeting_threshold": years_meeting,
                "historical_match_rate": rate,
                "comparison_direction": "PROJECT_WORKING_ASSUMPTION_NOT_OFFICIALLY_VERIFIED",
                "interpretation_status": status,
                "data_quality_warning": (
                    "Missing values excluded from denominator; cutoff/rank semantics and direction remain unconfirmed"
                ),
            }
        )
    return pd.DataFrame(rows)


def add_report_header(lines: list[str], frame: pd.DataFrame) -> None:
    lines.extend(
        [
            "STAGE 10 - HISTORICAL CUTOFF/RANK COMPARISON ENGINE",
            "====================================================",
            "",
            "This is a historical threshold comparison prototype, not an admission probability model.",
            "No result is a guarantee, safe-college label, confirmed admission, or seat probability.",
            "",
            "1. INPUT ASSUMPTIONS",
            "--------------------",
            "- Source file is inspected read-only.",
            "- Exact branch_code matching is used; branch_name substring matching is not used.",
            "- Category values are mapped to exactly one cutoff or rank column.",
            "- Missing historical values are excluded from the denominator and never treated as zero.",
            "- The comparison rules below are PROJECT WORKING ASSUMPTIONS only.",
            "- Stage 8 and Stage 9 found that official cutoff/rank semantics and directions remain unconfirmed.",
            "",
            "2. DATASET VALIDATION",
            "---------------------",
            f"Input path: {INPUT_PATH}",
            f"Rows: {len(frame)}",
            f"Columns: {len(frame.columns)}",
            f"Years available: {sorted(int(value) for value in frame['year'].unique())}",
            f"Primary-key duplicate rows: {int(frame.duplicated(KEY_COLUMNS).sum())}",
            f"Categories: {CATEGORIES}",
            f"Category mapping: {CATEGORY_COLUMNS}",
            "",
            "3. COMPARISON RULES",
            "--------------------",
            f"Cutoff working rule: {WORKING_ASSUMPTIONS['cutoff']}",
            f"Rank working rule: {WORKING_ASSUMPTIONS['rank']}",
            "Comparison direction status: UNCONFIRMED OFFICIAL SEMANTICS.",
            "The working rules are used only to demonstrate transparent historical comparison and must not be presented as official interpretations.",
            "",
            "4. MISSING-DATA HANDLING",
            "------------------------",
            "- Missing values remain missing.",
            "- A missing year is not a failed comparison and is not a successful comparison.",
            "- years_with_usable_data is the denominator for historical_match_rate.",
            "- If no usable values exist, the result is No comparable records and the rate is unavailable.",
            "- One usable year is labelled Insufficient historical data.",
        ]
    )
    for mapping in CATEGORY_COLUMNS.values():
        for column in mapping.values():
            lines.append(f"  {column}: missing={int(frame[column].isna().sum())}")
    lines.extend(
        [
            "",
            "5. EXECUTION RESULTS",
            "--------------------",
        ]
    )


def append_results(lines: list[str], args: argparse.Namespace, results: pd.DataFrame) -> None:
    lines.extend(
        [
            f"District input: {args.district}",
            f"Exact branch_code input: {args.branch_code}",
            f"Category input: {args.category}",
            f"Input type: {args.input_type}",
            f"Student value: {args.student_value}",
            f"Selected years: {args.years}",
            f"Matching college/course groups: {len(results)}",
            "",
            "Results:",
        ]
    )
    if results.empty:
        lines.append("No matching records for the requested district, exact branch_code, years, and category value.")
        return
    for row in results.itertuples(index=False):
        lines.extend(
            [
                f"College: {row.college_name} (code={row.college_code})",
                f"District: {row.district}",
                f"Branch: {row.branch_name} (code={row.branch_code})",
                f"Observed college-name variants: {row.observed_college_names}",
                f"Observed branch-name variants: {row.observed_branch_names}",
                f"Category/input: {row.category}/{row.input_type}",
                f"Historical values by year: {row.historical_values_by_year}",
                f"Meets threshold by year: {row.meets_threshold_by_year}",
                f"Usable years: {row.usable_years}",
                f"Missing years: {row.missing_years}",
                f"Years meeting threshold: {row.years_meeting_threshold}",
                f"Historical threshold-match rate: {('UNAVAILABLE' if pd.isna(row.historical_match_rate) else f'{row.historical_match_rate:.2%}')}",
                f"Comparison direction: {row.comparison_direction}",
                f"Interpretation status: {row.interpretation_status}",
                f"Data-quality warning: {row.data_quality_warning}",
                "",
            ]
        )


def append_limitations(lines: list[str]) -> None:
    lines.extend(
        [
            "6. LIMITATIONS",
            "---------------",
            "- Historical cutoff/rank values are not confirmed individual admission outcomes.",
            "- This engine does not calculate admission probability.",
            "- Counselling round and source statistic definitions remain unknown.",
            "- Student preferences, seat availability, allocation rules, and applicant behavior are not represented.",
            "- Missing category values reduce evidence and are excluded rather than imputed.",
            "- A prediction year may differ from reference years and should be evaluated chronologically.",
            "",
            "7. EXAMPLE EXECUTION",
            "--------------------",
            "python stage10_historical_comparison.py --district COIMBATORE --branch-code CS --category OC --input-type cutoff --student-value 190 --years 2021,2022,2023,2024,2025",
            "This example uses project working assumptions only and does not produce an admission probability.",
            "",
            "8. ML SUITABILITY",
            "------------------",
            "This engine is not an ML training pipeline and creates no engineered features or target labels.",
            "Its output may serve as transparent historical evidence, but it is not a validated ML target or calibrated probability.",
            "Actual model development requires confirmed source semantics, a prediction timestamp, target eligibility rules, and outcome validation.",
            "",
            "9. FINAL STATUS",
            "----------------",
            "Historical threshold comparison completed: YES",
            "Official cutoff/rank semantics verified: NO",
            "Official comparison direction verified: NO",
            "Admission probabilities generated: NO",
            "Source CSV modified: NO",
            "Existing project files modified: NO",
            "ML model trained: NO",
            f"Report path: {REPORT_PATH}",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 10 exact-branch historical comparison engine")
    parser.add_argument("--district", required=True)
    parser.add_argument("--branch-code", required=True)
    parser.add_argument("--category", required=True)
    parser.add_argument("--input-type", required=True, choices=["cutoff", "rank"])
    parser.add_argument("--student-value", required=True, type=float)
    parser.add_argument("--years", required=True, help="comma-separated years, e.g. 2021,2022,2023")
    args = parser.parse_args()

    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"input file not found: {INPUT_PATH}")
    source_hash_before = sha256(INPUT_PATH)
    frame = pd.read_csv(INPUT_PATH)
    validate_frame(frame)
    years = parse_years(args.years)
    validate_inputs(frame, args.district, args.branch_code, args.category.upper(), args.input_type, args.student_value, years)
    args.category = args.category.upper()
    args.years = years
    results = comparison_results(
        frame,
        args.district,
        args.branch_code,
        args.category,
        args.input_type,
        args.student_value,
        years,
    )

    lines: list[str] = []
    add_report_header(lines, frame)
    append_results(lines, args, results)
    append_limitations(lines)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if sha256(INPUT_PATH) != source_hash_before:
        raise RuntimeError("source CSV hash changed during execution")

    print("STAGE 10 HISTORICAL COMPARISON COMPLETE")
    print(f"District: {args.district}")
    print(f"Exact branch_code: {args.branch_code}")
    print(f"Category/input: {args.category}/{args.input_type}")
    print(f"Selected years: {years}")
    print(f"Matching college/course groups: {len(results)}")
    print("Comparison rules: PROJECT WORKING ASSUMPTIONS; official semantics unconfirmed")
    print("No admission probability generated")
    print("Source CSV unchanged: True")
    print(f"Report created successfully: {REPORT_PATH}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, FileNotFoundError, RuntimeError) as error:
        print(f"STAGE 10 FAILED: {error}")
        raise SystemExit(1) from error
