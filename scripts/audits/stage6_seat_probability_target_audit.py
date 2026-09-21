from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = ROOT / "data" / "integrated" / "tnea_integrated_master.csv"
REPORT_PATH = ROOT / "documentation" / "seat_target_feasibility_report.txt"
KEY_COLUMNS = ["year", "college_code", "branch_code"]
CATEGORIES = ["oc", "bc", "bcm", "mbc", "sc", "sca", "st"]
CUTOFF_COLUMNS = [f"cutoff_{category}" for category in CATEGORIES]
RANK_COLUMNS = [f"rank_{category}" for category in CATEGORIES]
CUTOFF_PARTIAL_COLUMNS = [f"cutoff_{category}_partial" for category in CATEGORIES]
RANK_PARTIAL_COLUMNS = [f"rank_{category}_partial" for category in CATEGORIES]
PARTIAL_COLUMNS = CUTOFF_PARTIAL_COLUMNS + RANK_PARTIAL_COLUMNS
REQUIRED_COLUMNS = [
    "year",
    "college_code",
    "college_name",
    "district",
    "college_type",
    "branch_code",
    "branch_name",
] + CUTOFF_COLUMNS + RANK_COLUMNS + PARTIAL_COLUMNS


def pct(value: int, total: int) -> str:
    return f"{100 * value / total:.2f}%" if total else "0.00%"


def list_text(values: list[object], limit: int = 25) -> str:
    shown = [str(value) for value in values[:limit]]
    suffix = " ..." if len(values) > limit else ""
    return ", ".join(shown) + suffix if shown else "None"


def fmt(value: object) -> str:
    if pd.isna(value):
        return "NA"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def validate_input(frame: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Input is missing required columns: {missing}")


def target_measure(column: str) -> str:
    return "cutoff" if column.startswith("cutoff_") else "rank"


def target_category(column: str) -> str:
    return column.split("_")[-1].upper()


def add_target_inventory(lines: list[str], frame: pd.DataFrame) -> None:
    lines.extend(
        [
            "6. Cutoff/Rank Analysis",
            "------------------------",
            "Cutoff and rank values are reported separately. This audit does not assume their direction, meaning, or interchangeability.",
            "",
            "Target | Measure | Category | Available | Missing | Missing % | Min | Max | Partial columns",
        ]
    )
    for column in CUTOFF_COLUMNS + RANK_COLUMNS:
        values = pd.to_numeric(frame[column], errors="coerce")
        valid = values.dropna()
        partial = (
            f"cutoff_{target_category(column).lower()}_partial, rank_{target_category(column).lower()}_partial"
        )
        lines.append(
            f"{column} | {target_measure(column)} | {target_category(column)} | {values.notna().sum()} | "
            f"{values.isna().sum()} | {pct(int(values.isna().sum()), len(frame))} | "
            f"{fmt(valid.min() if len(valid) else None)} | {fmt(valid.max() if len(valid) else None)} | {partial}"
        )
    lines.extend(
        [
            "",
            "Year-wise availability:",
        ]
    )
    for year in sorted(frame["year"].unique()):
        subset = frame[frame["year"] == year]
        lines.append(f"Year {year} ({len(subset)} rows):")
        for column in CUTOFF_COLUMNS + RANK_COLUMNS:
            available = int(pd.to_numeric(subset[column], errors="coerce").notna().sum())
            lines.append(f"  {column}: available={available}, missing={len(subset) - available}")
    lines.extend(
        [
            "",
            "Interpretation limits:",
            "- The dataset contains historical cutoff and rank-related values, but this audit does not infer whether higher or lower is preferable.",
            "- A student's cutoff can be compared with historical cutoff values only after the cutoff definition and direction are confirmed.",
            "- A student's rank can be compared with historical rank values only after the rank definition and direction are confirmed.",
            "- Missing category values and partial records remain missing; they are not replaced or treated as zero.",
            "- No admission-round field was identified in the integrated schema, so round-specific comparisons cannot be verified here.",
        ]
    )


def add_filter_analysis(lines: list[str], frame: pd.DataFrame) -> None:
    coimbatore = frame[frame["district"].astype(str).str.strip().str.upper() == "COIMBATORE"]
    cse_tokens = coimbatore[coimbatore["branch_name"].astype(str).str.contains("COMPUTER SCIENCE", case=False, na=False)]
    lines.extend(
        [
            "4. District/Course Filtering Feasibility",
            "-----------------------------------------",
            "Supported filter columns: district, branch_code, branch_name, and year.",
            "The primary identifier for a course is branch_code; branch_name is retained as descriptive evidence.",
            "",
            "Illustrative requested filter inspection: district=Coimbatore, course search token=COMPUTER SCIENCE",
            f"Rows in COIMBATORE district: {len(coimbatore)}",
            f"Matching rows whose branch_name contains COMPUTER SCIENCE: {len(cse_tokens)}",
            f"Matching college codes: {cse_tokens['college_code'].nunique() if len(cse_tokens) else 0}",
            "Matching colleges:",
        ]
    )
    if len(cse_tokens):
        college_rows = cse_tokens[["college_code", "college_name", "branch_code", "branch_name"]].drop_duplicates()
        for row in college_rows.itertuples(index=False):
            lines.append(
                f"  college_code={row.college_code}; college_name={row.college_name}; "
                f"branch_code={row.branch_code}; branch_name={row.branch_name}"
            )
    else:
        lines.append("  No rows matched this search in the actual dataset.")
    duplicate_count = int(cse_tokens.duplicated(["year", "college_code", "branch_code"]).sum()) if len(cse_tokens) else 0
    lines.extend(
        [
            f"Duplicate college/course/year records in this filtered set: {duplicate_count}",
            f"Distinct matching branch codes: {list_text(sorted(cse_tokens['branch_code'].unique().tolist())) if len(cse_tokens) else 'None'}",
            f"Distinct matching branch names: {list_text(sorted(cse_tokens['branch_name'].unique().tolist())) if len(cse_tokens) else 'None'}",
            "",
            "Filter limitations:",
            "- The dataset does not contain a separate normalized 'CSE' field.",
            "- A UI must define an explicit mapping or search policy for a user-entered course such as CSE.",
            "- Branch code and branch name must be inspected together; this audit does not assume every similar name is the same course.",
            "- District and course filters can identify historical records, but they do not by themselves establish admission probability.",
        ]
    )


def add_input_feasibility(lines: list[str]) -> None:
    lines.extend(
        [
            "3. Application Input Feasibility",
            "--------------------------------",
            "Input | Supported by current data | Relevant columns | Main concern",
            "Student cutoff | Partially supported | cutoff_OC/BC/BCM/MBC/SC/SCA/ST | Category-specific missingness; definition, scale, direction, and timing must be confirmed.",
            "Student rank | Partially supported | rank_OC/BC/BCM/MBC/SC/SCA/ST | Rank meaning, direction, timing, and missingness must be confirmed.",
            "Community/category | Supported as wide category columns | OC, BC, BCM, MBC, SC, SCA, ST column families | There is no row-level category field; UI category must map explicitly to a column family.",
            "Preferred district | Supported | district | Validate against actual values and handle no-match input.",
            "Preferred course | Partially supported | branch_code, branch_name | No separate normalized course/CSE field; course mapping requires a defined policy.",
            "Admission year | Supported | year | Must be constrained to available years and tied to a time-aware evaluation design.",
            "Optional college type | Supported | college_type | Validate actual values; future availability must be confirmed.",
            "",
            "Cutoff and rank cannot be used interchangeably based on this dataset. They are separate column groups with different observed numeric ranges and no documented equivalence in the CSV.",
        ]
    )


def add_college_wise_design(lines: list[str], frame: pd.DataFrame) -> None:
    group = frame.groupby(["college_code", "branch_code"], dropna=False)
    years_per_combo = group["year"].nunique()
    records_per_combo = group.size()
    missing_summary = []
    for column in CUTOFF_COLUMNS + RANK_COLUMNS:
        missing_summary.append(f"{column} missing={int(frame[column].isna().sum())}")
    lines.extend(
        [
            "5. College-Wise Prediction Feasibility",
            "---------------------------------------",
            "Observed unit: one row per year + college_code + branch_code, with category values in columns.",
            f"College-course combinations: {len(group)}",
            f"Combinations with multiple historical years: {int((years_per_combo > 1).sum())}",
            f"Combinations with exactly one historical year: {int((years_per_combo == 1).sum())}",
            f"Maximum years observed for one combination: {int(years_per_combo.max())}",
            f"Combinations with multiple records: {int((records_per_combo > 1).sum())}",
            "",
            "Historical eligibility comparison: potentially supportable if a student input can be defined and compared to a documented historical threshold.",
            "College ranking by historical suitability: potentially supportable as a descriptive score or comparison, subject to missingness and temporal validation.",
            "Calibrated seat probability: not supported by this dataset alone because no confirmed admission outcome, seat allocation outcome, applicant competition context, or calibration evidence is present.",
            "True admission outcome prediction: not supported by this dataset alone; actual outcome labels and prediction-time information are required.",
            "",
            "Category data completeness snapshot:",
            "  " + "; ".join(missing_summary),
            "",
            "The intended application can return one historical record-based result per matching college/course, but the result must be labeled as a historical comparison or eligibility estimate until outcome validation exists.",
        ]
    )


def add_targets(lines: list[str]) -> None:
    lines.extend(
        [
            "7. Target Definition Comparison",
            "--------------------------------",
            "Target A - Historical eligibility indicator",
            "  Required data: student cutoff or rank, category, year, college/course, and a documented threshold comparison rule.",
            "  Current support: potentially supportable as a rule-based historical comparison; the data contains thresholds but not confirmed outcomes.",
            "  Limitations: missing values, partial records, changing competition, ambiguous cutoff/rank definitions, and year mismatch.",
            "  Assumption: a threshold comparison is not the same as admission confirmation.",
            "",
            "Target B - Historical admission likelihood score",
            "  Required data: repeated historical observations and a defined scoring rule for how often a student would meet historical thresholds.",
            "  Current support: potentially supportable as a descriptive score if clearly labeled and evaluated chronologically.",
            "  Limitations: the score would summarize historical threshold comparisons, not calibrated probability of obtaining a seat.",
            "  Assumption: any score-to-probability interpretation would require validation and must not be invented.",
            "",
            "Target C - Actual admission probability",
            "  Required data: confirmed admission outcomes or seat-allocation outcomes, prediction-time features, and calibration/validation data.",
            "  Current support: not supported by the current integrated dataset alone.",
            "  Limitations: historical cutoff/rank values do not prove that a student was admitted or obtained a seat.",
            "  Required additional evidence: actual outcomes, seat matrix/availability, applicant behavior or allocation records, and a defined prediction timestamp.",
            "",
            "No target is selected automatically by this audit.",
        ]
    )


def add_validation_design(lines: list[str]) -> None:
    lines.extend(
        [
            "10. Historical Validation Design",
            "--------------------------------",
            "A non-model evaluation could derive comparison rules from earlier years, validate on a later year, and reserve the latest available year for testing.",
            "",
            "Potential design: derive from 2021-2023, validate on 2024, test on 2025.",
            "Alternative design: derive from 2021-2024, test on 2025.",
            "",
            "Leakage risks to review before implementation:",
            "- Future-year cutoff or rank values used while evaluating an earlier year.",
            "- Same-year cutoff or rank values published after the prediction timestamp.",
            "- Other category values that encode post-event information.",
            "- Partial indicators whose generation depends on outcome availability.",
            "- College/branch identifiers that permit memorization or encode future changes.",
            "- Any field updated after the student input would supposedly be known.",
            "",
            "No columns are removed by this audit. The safe feature set depends on the intended application timestamp.",
        ]
    )


def add_edge_cases(lines: list[str]) -> None:
    lines.extend(
        [
            "11. Missing-Data Concerns and Edge Cases",
            "---------------------------------------",
            "- District with no matching course: return no comparable records; do not invent a probability.",
            "- College with no category data: label insufficient historical data for that category.",
            "- Missing cutoff or rank: preserve missingness and do not compare as zero.",
            "- Missing partial indicator: flag the record for review; do not infer its meaning.",
            "- Student provides cutoff but not rank: use only a cutoff-specific comparison if the cutoff definition is confirmed.",
            "- Student provides rank but not cutoff: use only a rank-specific comparison if the rank definition is confirmed.",
            "- Invalid category, course, or district: validate against explicit allowed values/mappings and return a clear input error.",
            "- New college or branch: report no historical comparable records unless a documented mapping exists.",
            "- Very sparse category: label low evidence and avoid calibrated probability claims.",
            "- College/course with one historical year: show limited historical evidence and avoid overconfident estimates.",
        ]
    )


def add_human_decisions(lines: list[str]) -> None:
    lines.extend(
        [
            "12. Required Human Decisions",
            "----------------------------",
            "1. Should the application accept cutoff, rank, or both?",
            "2. Is the target historical eligibility, a descriptive historical score, or actual admission probability?",
            "3. Which admission year should be predicted and when is the prediction made?",
            "4. Which categories should be supported?",
            "5. Should all matching colleges be shown?",
            "6. How should missing category data be handled?",
            "7. Should output use a probability, score, or eligibility label?",
            "8. Which data is available at the prediction timestamp?",
            "9. How should new colleges and branches be handled?",
            "10. What historical outcome data is needed to validate predictions?",
        ]
    )


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_PATH}")
    frame = pd.read_csv(INPUT_PATH)
    validate_input(frame)

    lines = [
        "STAGE 6 - SEAT PROBABILITY TARGET AND APPLICATION FEASIBILITY AUDIT",
        "===================================================================",
        "",
        "1. Audit Objective",
        "-------------------",
        "Evaluate whether the integrated TNEA dataset supports college-wise historical eligibility estimates, descriptive historical scores, or actual admission probability predictions.",
        "This is a read-only feasibility and target-definition audit.",
        "No probabilities are generated and no target is selected automatically.",
        "",
        "2. Dataset Summary",
        "------------------",
        f"Input file: {INPUT_PATH}",
        f"Rows: {len(frame)}",
        f"Columns: {len(frame.columns)}",
        f"Column names: {list(frame.columns)}",
        "Data types:",
    ]
    lines.extend(f"  {column}: {dtype}" for column, dtype in frame.dtypes.items())
    lines.extend(
        [
            f"Year range: {frame['year'].min()}-{frame['year'].max()}",
            f"Years: {sorted(frame['year'].unique().tolist())}",
            f"District values ({frame['district'].nunique()}): {list_text(sorted(frame['district'].dropna().unique().tolist()))}",
            f"College codes: {frame['college_code'].nunique()}",
            f"College names: {frame['college_name'].nunique()}",
            f"Branch codes: {frame['branch_code'].nunique()}",
            f"Branch names: {frame['branch_name'].nunique()}",
            f"College types ({frame['college_type'].nunique()}): {list_text(sorted(frame['college_type'].dropna().unique().tolist()))}",
            f"Category-related columns: {CATEGORIES}",
            f"Cutoff columns: {CUTOFF_COLUMNS}",
            f"Rank columns: {RANK_COLUMNS}",
            f"Partial indicator columns: {PARTIAL_COLUMNS}",
            "Identifiable from current data: college=college_code/name; branch=branch_code/name; district=district; year=year; category=wide category column family; historical cutoff=cutoff_*; historical rank=rank_*.",
            "",
        ]
    )

    add_input_feasibility(lines)
    lines.extend(["", ""])
    add_filter_analysis(lines, frame)
    lines.extend(["", ""])
    add_college_wise_design(lines, frame)
    lines.extend(["", ""])
    add_target_inventory(lines, frame)
    lines.extend(["", ""])
    add_targets(lines)
    lines.extend(["", ""])
    lines.extend(
        [
            "8. Actual Admission Probability Limitations",
            "--------------------------------------------",
            "The current dataset does not contain confirmed student-level admission outcomes or a seat-allocation outcome label.",
            "Therefore it cannot, by itself, justify a calibrated percentage for the probability that a particular student obtains a particular seat.",
            "A threshold comparison or historical score may be displayed only with an explicit label such as 'Historical eligibility estimate', 'Historical threshold comparison', 'Insufficient historical data', or 'No comparable records'.",
            "The illustrative percentages in the request are not generated or treated as real values.",
            "",
            "9. Cutoff/Rank Interpretation and Comparison Design",
            "---------------------------------------------------",
            "A student cutoff may be compared to historical cutoff values only after the cutoff definition, scale, category, and direction are documented.",
            "A student rank may be compared to historical rank values only after the rank definition, scale, category, and direction are documented.",
            "Cutoff and rank inputs cannot be substituted for one another without evidence.",
            "Different years, missing category values, partial records, and unobserved admission rounds can make historical comparisons non-comparable.",
            "",
        ]
    )
    add_validation_design(lines)
    lines.extend(["", ""])
    add_edge_cases(lines)
    lines.extend(["", ""])
    add_human_decisions(lines)
    lines.extend(
        [
            "",
            "13. Final Recommendation for Next Development Stage",
            "------------------------------------------------------",
            "A. College-wise historical eligibility estimates: potentially supportable with a documented cutoff/rank comparison rule, explicit category mapping, missing-data labels, and chronological validation.",
            "B. College-wise actual admission probability predictions: not supportable from this dataset alone because confirmed admission outcomes and calibration evidence are absent.",
            "C. Both: possible only if the historical comparison is clearly separated from a future outcome model and additional outcome/timing data is obtained for probability claims.",
            "",
            "Recommended next stage: resolve the human decisions above, define the prediction timestamp and target, and obtain or verify outcome data before model development.",
            "",
            "14. Audit Completion",
            "--------------------",
            "Audit completed successfully: YES",
            "Input CSV modified: NO",
            "Source CSV modified: NO",
            "Rows deleted: NO",
            "Missing values filled: NO",
            "Feature engineering performed: NO",
            "ML model trained: NO",
            "Invented probabilities generated: NO",
            f"Report path: {REPORT_PATH}",
        ]
    )

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("STAGE 6 FEASIBILITY AUDIT COMPLETE")
    print(f"Rows audited: {len(frame)}")
    print(f"Years: {sorted(frame['year'].unique().tolist())}")
    print(f"Districts: {frame['district'].nunique()}")
    print(f"College-course combinations: {frame.groupby(['college_code', 'branch_code']).ngroups}")
    print("Historical eligibility comparison: potentially supportable with defined rules")
    print("Actual calibrated admission probability: not supported by current data alone")
    print("No probabilities generated; no CSV modified.")
    print(f"Report created successfully: {REPORT_PATH}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, FileNotFoundError) as error:
        print(f"STAGE 6 AUDIT FAILED: {error}")
        raise SystemExit(1) from error
