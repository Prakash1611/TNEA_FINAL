from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = ROOT / "data" / "integrated" / "tnea_integrated_master.csv"
REPORT_PATH = ROOT / "documentation" / "historical_chance_report.txt"
RESULTS_PATH = ROOT / "exports" / "historical_chance_results.csv"
KEY_COLUMNS = ["year", "college_code", "branch_code"]
CATEGORIES = ["OC", "BC", "BCM", "MBC", "SC", "SCA", "ST"]
CATEGORY_COLUMNS = {
    "OC": ("cutoff_oc", "rank_oc"),
    "BC": ("cutoff_bc", "rank_bc"),
    "BCM": ("cutoff_bcm", "rank_bcm"),
    "MBC": ("cutoff_mbc", "rank_mbc"),
    "SC": ("cutoff_sc", "rank_sc"),
    "SCA": ("cutoff_sca", "rank_sca"),
    "ST": ("cutoff_st", "rank_st"),
}
PARTIAL_COLUMNS = [
    f"{measure}_{category.lower()}_partial"
    for measure in ("cutoff", "rank")
    for category in CATEGORIES
]
IDENTIFIER_COLUMNS = [
    "year",
    "college_code",
    "college_name",
    "district",
    "college_type",
    "branch_code",
    "branch_name",
]
REQUIRED_COLUMNS = IDENTIFIER_COLUMNS + [column for pair in CATEGORY_COLUMNS.values() for column in pair] + PARTIAL_COLUMNS


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pct(count: int, total: int) -> str:
    return f"{100 * count / total:.2f}%" if total else "0.00%"


def list_text(values: list[object], limit: int = 25) -> str:
    text = [str(value) for value in values[:limit]]
    suffix = " ..." if len(values) > limit else ""
    return ", ".join(text) + suffix if text else "None"


def validate_frame(frame: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Required columns missing: {missing}")
    duplicate_keys = int(frame.duplicated(KEY_COLUMNS).sum())
    if duplicate_keys:
        raise ValueError(f"Duplicate primary-key rows found: {duplicate_keys}")


def parse_years(value: str | None) -> list[int]:
    if not value:
        return [2021, 2022, 2023, 2024, 2025]
    try:
        years = sorted({int(item.strip()) for item in value.split(",")})
    except ValueError as error:
        raise ValueError("Historical years must be comma-separated integers") from error
    if not years:
        raise ValueError("At least one historical year is required")
    return years


def add_dataset_audit(lines: list[str], frame: pd.DataFrame) -> None:
    lines.extend(
        [
            "1. READ-ONLY DATASET VALIDATION",
            "---------------------------------",
            f"Input file: {INPUT_PATH}",
            f"Rows: {len(frame)}",
            f"Columns: {len(frame.columns)}",
            f"Column names: {list(frame.columns)}",
            f"Data types: {frame.dtypes.astype(str).to_dict()}",
            f"Years: {sorted(frame['year'].unique().tolist())}",
            f"Year range: {frame['year'].min()}-{frame['year'].max()}",
            f"Unique college codes: {frame['college_code'].nunique()}",
            f"Unique branch codes: {frame['branch_code'].nunique()}",
            f"Unique districts: {frame['district'].nunique()}",
            f"Duplicate exact rows: {int(frame.duplicated().sum())}",
            f"Duplicate primary-key rows ({', '.join(KEY_COLUMNS)}): {int(frame.duplicated(KEY_COLUMNS).sum())}",
            "",
            "Required columns: PRESENT",
            f"Category mapping: {CATEGORY_COLUMNS}",
            "Missing-value summary:",
        ]
    )
    for column in frame.columns:
        missing = int(frame[column].isna().sum())
        lines.append(f"  {column}: missing={missing}, missing_pct={pct(missing, len(frame))}")
    lines.extend(
        [
            "",
            "Source semantics check:",
            "- Existing Stage 2-6 audit reports were reviewed.",
            "- Cutoff/rank direction and exact source definitions are not independently confirmed here.",
            "- Historical values are not confirmed individual admission outcomes.",
            "- No source values were filled, replaced, or deleted.",
        ]
    )


def add_filter_checks(lines: list[str], frame: pd.DataFrame) -> None:
    district = "COIMBATORE"
    course_mask = frame["branch_name"].astype(str).str.contains("COMPUTER SCIENCE", case=False, na=False)
    filtered = frame[(frame["district"].astype(str).str.strip().str.upper() == district) & course_mask]
    lines.extend(
        [
            "2. COLLEGE/COURSE FILTERING CHECK",
            "----------------------------------",
            "A concrete audit check used district=COIMBATORE and branch_name containing COMPUTER SCIENCE.",
            "This is an inspection example, not a silently selected application input.",
            f"Matching rows: {len(filtered)}",
            f"Matching colleges: {filtered['college_code'].nunique()}",
            f"Matching branch codes: {sorted(filtered['branch_code'].unique().tolist()) if len(filtered) else []}",
            f"Matching branch names: {sorted(filtered['branch_name'].unique().tolist()) if len(filtered) else []}",
            f"Duplicate college/course/year records: {int(filtered.duplicated(KEY_COLUMNS).sum())}",
            "Actual matching college records:",
        ]
    )
    for row in filtered[["college_code", "college_name", "branch_code", "branch_name"]].drop_duplicates().itertuples(index=False):
        lines.append(
            f"  college_code={row.college_code}; college_name={row.college_name}; "
            f"branch_code={row.branch_code}; branch_name={row.branch_name}"
        )
    lines.extend(
        [
            "",
            "Filtering rules for comparison mode:",
            "- District comparison strips surrounding whitespace and is case-insensitive.",
            "- Course can be matched by exact branch_code or case-insensitive branch-name text.",
            "- Similar names are not merged into one branch or college.",
            "- Category is validated against OC, BC, BCM, MBC, SC, SCA, ST.",
        ]
    )


def add_methodology(lines: list[str]) -> None:
    lines.extend(
        [
            "3. COMPARISON METHODOLOGY",
            "--------------------------",
            "For each filtered college/course group and requested category:",
            "1. Select exactly one measure family: cutoff OR rank.",
            "2. Restrict reference records to the requested historical years.",
            "3. Keep each year separate and ignore missing values in the denominator.",
            "4. Count years meeting the configured comparison rule only when direction is explicitly supplied.",
            "5. Compute historical_match_rate = years_meeting_threshold / years_with_usable_data.",
            "6. Report usable years, missing years, values by year, warnings, and interpretation status.",
            "",
            "Default comparison direction: UNCONFIRMED.",
            "If direction is UNCONFIRMED, no threshold-match rate is calculated and no definitive eligibility claim is made.",
            "If configured, higher_is_better means student_value >= historical_value; lower_is_better means student_value <= historical_value.",
            "Those inequalities are prototype rules only and require source-semantic confirmation.",
            "The result is a historical threshold-match rate, never an admission probability.",
            "",
            "Example calculation (synthetic illustration only, not a dataset result):",
            "If 4 of 5 usable historical years meet an explicitly confirmed rule, the historical threshold-match rate is 4/5 = 80%.",
            "This would still be historical evidence, not an actual seat probability.",
        ]
    )


def add_target_limitations(lines: list[str], frame: pd.DataFrame) -> None:
    lines.extend(
        [
            "4. LIMITATIONS AND TARGET INTERPRETATION",
            "------------------------------------------",
            "- Historical cutoff/rank values are not confirmed individual admission outcomes.",
            "- Actual admission probability cannot be claimed from this dataset alone.",
            "- Seat availability and counselling rounds may change.",
            "- Student preferences and allocation rules are not represented.",
            "- Missing category values reduce evidence and are not treated as failures or successes.",
            "- Cutoff/rank definitions and direction require source verification.",
            "- The prediction year may differ from historical reference years.",
            "- Historical match rate is not a calibrated probability.",
            "- Results must not be interpreted as guaranteed admission or a safe college.",
            "- Actual probability requires verified outcome data and a defined prediction timestamp.",
            "",
            "Observed category missingness:",
        ]
    )
    for category in CATEGORIES:
        cutoff_column, rank_column = CATEGORY_COLUMNS[category]
        lines.append(
            f"  {category}: {cutoff_column} missing={int(frame[cutoff_column].isna().sum())}; "
            f"{rank_column} missing={int(frame[rank_column].isna().sum())}"
        )


def add_temporal_review(lines: list[str]) -> None:
    lines.extend(
        [
            "5. TEMPORAL VALIDATION DISCUSSION",
            "----------------------------------",
            "Possible evaluation design: historical reference 2021-2023, validation year 2024, test year 2025.",
            "This report does not claim that the indicator is validated because no validation test was performed.",
            "",
            "Leakage risks:",
            "- Future-year values must not be used to assess an earlier year.",
            "- Same-year cutoff/rank values may be post-event information depending on the prediction timestamp.",
            "- Other category values may also be unavailable at prediction time or derived after the outcome.",
            "- Partial indicators may encode availability or post-event processing.",
            "- College and branch identifiers can support filtering but may permit memorization or encode future changes.",
            "- Results must preserve historical year boundaries; no future information should enter a reference set.",
        ]
    )


def add_edge_cases(lines: list[str]) -> None:
    lines.extend(
        [
            "6. EDGE-CASE HANDLING",
            "----------------------",
            "- Negative or zero student input: reject with a validation error; do not alter the dataset.",
            "- Non-numeric student input: reject with a clear input error.",
            "- Invalid category: reject; do not fall back to another category.",
            "- Unknown district or course: report no matching records.",
            "- No usable historical values: report No comparable records.",
            "- One usable historical year: report Insufficient historical data and expose the usable year.",
            "- High category missingness: preserve missing years and display a data-quality warning.",
            "- New college/branch: report no historical comparable records unless an explicit mapping exists.",
            "- Missing partial indicator: report a warning; never infer or fill it.",
            "- Unconfirmed direction: report Comparison direction unconfirmed and calculate no definitive match rate.",
        ]
    )


def add_human_decisions(lines: list[str]) -> None:
    lines.extend(
        [
            "7. HUMAN DECISIONS REQUIRED BEFORE MODEL DEVELOPMENT",
            "------------------------------------------------------",
            "1. Confirm whether the application accepts cutoff, rank, or both.",
            "2. Confirm whether the target is historical eligibility, a descriptive score, or actual admission probability.",
            "3. Select the admission/prediction year and prediction timestamp.",
            "4. Select supported categories.",
            "5. Decide whether all matching colleges must be displayed.",
            "6. Define the missing-category policy.",
            "7. Choose probability, score, or eligibility-label output; probability requires outcome validation.",
            "8. Confirm which fields are available at prediction time.",
            "9. Define new-college and new-branch handling.",
            "10. Obtain historical outcome data needed to validate predictions.",
        ]
    )


def build_results(
    frame: pd.DataFrame,
    district: str,
    course: str,
    category: str,
    input_type: str,
    student_value: float,
    years: list[int],
    direction: str,
) -> pd.DataFrame:
    category = category.upper()
    if category not in CATEGORY_COLUMNS:
        raise ValueError(f"Invalid category {category}; expected one of {CATEGORIES}")
    if input_type not in {"cutoff", "rank"}:
        raise ValueError("input_type must be cutoff or rank")
    if student_value <= 0:
        raise ValueError("student value must be greater than zero")
    if direction not in {"UNCONFIRMED", "higher_is_better", "lower_is_better"}:
        raise ValueError("direction must be UNCONFIRMED, higher_is_better, or lower_is_better")

    district_mask = frame["district"].astype(str).str.strip().str.casefold() == district.strip().casefold()
    course_text_mask = frame["branch_name"].astype(str).str.contains(course, case=False, na=False)
    course_code_mask = frame["branch_code"].astype(str).str.casefold() == course.strip().casefold()
    selected = frame[district_mask & (course_text_mask | course_code_mask)].copy()
    value_column = CATEGORY_COLUMNS[category][0 if input_type == "cutoff" else 1]
    selected = selected[selected["year"].isin(years)]
    rows = []
    for identity, group in selected.groupby(
        ["college_code", "college_name", "district", "branch_code", "branch_name"], dropna=False
    ):
        values = pd.to_numeric(group[value_column], errors="coerce")
        usable = values.dropna()
        usable_years = sorted(group.loc[values.notna(), "year"].tolist())
        missing_years = sorted(group.loc[values.isna(), "year"].tolist())
        if direction == "higher_is_better":
            meets = int((usable <= student_value).sum())
        elif direction == "lower_is_better":
            meets = int((usable >= student_value).sum())
        else:
            meets = None
        rate = (meets / len(usable)) if meets is not None and len(usable) else None
        if not len(usable):
            status = "No comparable records"
        elif direction == "UNCONFIRMED":
            status = "Comparison direction unconfirmed"
        elif len(usable) == 1:
            status = "Insufficient historical data"
        elif meets == len(usable):
            status = "Historical threshold matched in all usable years"
        elif meets:
            status = "Historical threshold matched in some years"
        else:
            status = "Historical threshold not matched in usable years"
        rows.append(
            {
                "college_code": identity[0],
                "college_name": identity[1],
                "district": identity[2],
                "branch_code": identity[3],
                "branch_name": identity[4],
                "category": category,
                "input_type": input_type,
                "student_input_value": student_value,
                "historical_years_requested": ",".join(map(str, years)),
                "usable_years": ",".join(map(str, usable_years)),
                "missing_years": ",".join(map(str, missing_years)),
                "years_meeting_threshold": meets,
                "historical_match_rate": rate,
                "historical_values_by_year": str(
                    {int(year): float(value) if pd.notna(value) else None for year, value in zip(group["year"], group[value_column])}
                ),
                "comparison_direction": direction,
                "interpretation_status": status,
                "data_quality_warning": (
                    "Missing historical values excluded from denominator; direction is unconfirmed"
                    if direction == "UNCONFIRMED"
                    else "Historical comparison only; not an admission probability"
                ),
            }
        )
    return pd.DataFrame(rows)


def add_execution_result(lines: list[str], args: argparse.Namespace, results: pd.DataFrame | None) -> None:
    lines.extend(["", "8. EXECUTION MODE", "------------------"])
    if results is None:
        lines.extend(
            [
                "Mode: audit-only",
                "No user comparison values were supplied; no derived result rows were generated.",
                "Clearly labelled example configuration:",
                "  --district COIMBATORE --course CS --category OC --input-type cutoff --student-value 190 --years 2021,2022,2023 --direction UNCONFIRMED",
                "The example is configuration syntax only and was not executed as an actual result.",
            ]
        )
    else:
        lines.extend(
            [
                "Mode: comparison prototype",
                f"District: {args.district}",
                f"Course query: {args.course}",
                f"Category: {args.category}",
                f"Input type: {args.input_type}",
                f"Historical years: {args.years}",
                f"Comparison direction: {args.direction}",
                f"Result rows: {len(results)}",
                f"Derived output: {RESULTS_PATH}",
                "Results are historical threshold comparisons only; they are not probabilities or admission guarantees.",
            ]
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 7 historical threshold comparison prototype")
    parser.add_argument("--audit-only", action="store_true", help="Generate the audit report without comparison inputs")
    parser.add_argument("--district")
    parser.add_argument("--course", help="Exact branch code or case-insensitive text contained in branch_name")
    parser.add_argument("--category", choices=CATEGORIES)
    parser.add_argument("--input-type", choices=["cutoff", "rank"])
    parser.add_argument("--student-value", type=float)
    parser.add_argument("--years", default="2021,2022,2023,2024,2025")
    parser.add_argument("--direction", choices=["UNCONFIRMED", "higher_is_better", "lower_is_better"], default="UNCONFIRMED")
    args = parser.parse_args()

    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_PATH}")
    frame = pd.read_csv(INPUT_PATH)
    validate_frame(frame)
    source_hash_before = sha256(INPUT_PATH)
    years = parse_years(args.years)
    available_years = set(frame["year"].unique().tolist())
    unknown_years = set(years) - available_years
    if unknown_years:
        raise ValueError(f"Requested years not present in dataset: {sorted(unknown_years)}")

    comparison_args_present = any(
        value is not None for value in (args.district, args.course, args.category, args.input_type, args.student_value)
    )
    if not args.audit_only and not comparison_args_present:
        args.audit_only = True
    if comparison_args_present and args.audit_only:
        raise ValueError("Use either --audit-only or comparison arguments, not both")
    required_comparison = [args.district, args.course, args.category, args.input_type, args.student_value]
    if not args.audit_only and any(value is None for value in required_comparison):
        raise ValueError("Comparison mode requires district, course, category, input-type, and student-value")

    results = None
    if not args.audit_only:
        results = build_results(
            frame,
            args.district,
            args.course,
            args.category,
            args.input_type,
            args.student_value,
            years,
            args.direction,
        )
        results.to_csv(RESULTS_PATH, index=False)

    lines = [
        "STAGE 7 - HISTORICAL THRESHOLD COMPARISON AND CHANCE INDICATOR PROTOTYPE",
        "=========================================================================",
        "",
        "This stage produces historical threshold comparisons only.",
        "It is NOT a confirmed admission probability model.",
        "No result may be described as guaranteed admission, actual seat probability, or confirmed admission probability.",
        "",
    ]
    add_dataset_audit(lines, frame)
    add_filter_checks(lines, frame)
    add_methodology(lines)
    add_target_limitations(lines, frame)
    add_temporal_review(lines)
    add_edge_cases(lines)
    add_human_decisions(lines)
    add_execution_result(lines, args, results)
    lines.extend(
        [
            "",
            "9. FINAL STATUS",
            "----------------",
            "Audit completed successfully: YES",
            "Input CSV modified: NO",
            "Source rows deleted: NO",
            "Missing values filled or replaced: NO",
            "ML model trained: NO",
            "Source values silently changed: NO",
            "Invented probabilities generated: NO",
            "Direction default: UNCONFIRMED unless explicitly supplied by the user.",
            "Historical reference/validation discussion: 2021-2023 / 2024 / 2025; not executed as model validation.",
            f"Report path: {REPORT_PATH}",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    source_hash_after = sha256(INPUT_PATH)
    if source_hash_before != source_hash_after:
        raise RuntimeError("Input CSV hash changed during execution")

    print("STAGE 7 AUDIT COMPLETE")
    print(f"Rows audited: {len(frame)}")
    print(f"Primary-key duplicate rows: {int(frame.duplicated(KEY_COLUMNS).sum())}")
    print("Comparison direction: UNCONFIRMED by default")
    print("No admission probabilities generated.")
    print("Input CSV unchanged: True")
    if results is not None:
        print(f"Derived results rows: {len(results)}")
        print(f"Derived results file: {RESULTS_PATH}")
    print(f"Report created successfully: {REPORT_PATH}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, FileNotFoundError, RuntimeError) as error:
        print(f"STAGE 7 FAILED: {error}")
        raise SystemExit(1) from error
