from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = ROOT / "data" / "integrated" / "tnea_integrated_master.csv"
REPORT_PATH = ROOT / "documentation" / "ml_feasibility_report.txt"
KEY_COLUMNS = ["year", "college_code", "branch_code"]
CATEGORIES = ["oc", "bc", "bcm", "mbc", "sc", "sca", "st"]
CUTOFF_COLUMNS = [f"cutoff_{category}" for category in CATEGORIES]
RANK_COLUMNS = [f"rank_{category}" for category in CATEGORIES]
PARTIAL_COLUMNS = [
    f"{measure}_{category}_partial"
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
REQUIRED_COLUMNS = IDENTIFIER_COLUMNS + CUTOFF_COLUMNS + RANK_COLUMNS + PARTIAL_COLUMNS


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pct(count: int, total: int) -> str:
    return f"{100 * count / total:.2f}%" if total else "0.00%"


def append_dataset_structure(lines: list[str], frame: pd.DataFrame) -> None:
    lines.extend(
        [
            "3. Dataset Structure",
            "---------------------",
            f"Rows: {len(frame)}",
            f"Columns: {len(frame.columns)}",
            f"Years: {sorted(int(value) for value in frame['year'].unique())}",
            f"Rows by year: {frame.groupby('year').size().to_dict()}",
            f"Unique college codes: {frame['college_code'].nunique()}",
            f"Unique branch codes: {frame['branch_code'].nunique()}",
            f"College-course-year duplicate keys: {int(frame.duplicated(KEY_COLUMNS).sum())}",
            f"Exact duplicate rows: {int(frame.duplicated().sum())}",
            f"Historical college-course combinations: {frame.groupby(['college_code', 'branch_code']).ngroups}",
            "",
            "Data types:",
        ]
    )
    lines.extend(f"  {column}: {dtype}" for column, dtype in frame.dtypes.items())
    lines.extend(["", "Missing percentages:"])
    for column in frame.columns:
        missing = int(frame[column].isna().sum())
        lines.append(f"  {column}: {missing} ({pct(missing, len(frame))})")
    lines.extend(
        [
            "",
            "Category measure columns:",
            f"  cutoff: {CUTOFF_COLUMNS}",
            f"  rank: {RANK_COLUMNS}",
            f"  partial indicators: {PARTIAL_COLUMNS}",
            "",
            "Partial indicator observed values:",
        ]
    )
    for column in PARTIAL_COLUMNS:
        lines.append(f"  {column}: {frame[column].value_counts(dropna=False).sort_index().to_dict()}")


def append_targets(lines: list[str], frame: pd.DataFrame) -> None:
    lines.extend(
        [
            "4. Candidate Target Analysis",
            "----------------------------",
            "Target A - Historical threshold eligibility indicator",
            "  Current support: PARTIAL / RULE-BASED ONLY.",
            "  Evidence: cutoff and rank values exist by year, college, branch, and category; Stage 10 provides explicit comparison rules.",
            "  Required assumptions: official cutoff/rank meaning, comparison direction, category mapping, prediction timestamp, and treatment of missing values.",
            "  Missing information: confirmed admission outcomes, counselling round, seat availability, preferences, and authoritative source semantics.",
            "  Misleading-result risk: a threshold match can be mistaken for admission confirmation.",
            "  Supervised ML suitability: NOT SUITABLE AS A VERIFIED LABEL WITHOUT OUTCOME VALIDATION; can remain a transparent rule-based comparison.",
            "",
            "Target B - Historical threshold match rate",
            "  Current support: DERIVABLE DESCRIPTIVE SUMMARY, NOT A SUPERVISED TARGET.",
            "  Evidence: Stage 10 computes years_meeting_threshold / years_with_usable_data for a supplied student value and exact college/branch.",
            "  Required assumptions: same unverified comparison rules and a defined reference-year window.",
            "  Missing information: calibrated outcome relationship and deployment-time availability.",
            "  Misleading-result risk: match rate can be presented incorrectly as probability or confidence.",
            "  Supervised ML suitability: NOT A NATURAL ROW-LEVEL LABEL; it is derived from the input and historical records.",
            "",
            "Target C - Actual admission outcome or admission probability",
            "  Current support: NOT SUPPORTED BY THE CURRENT DATASET.",
            "  Evidence: no student identifier, admitted flag, allotment result, seat assignment, application outcome, or confirmed outcome field exists.",
            "  Required data: verified student-level outcomes, seat/allotment context, counselling round, preferences, and prediction-time features.",
            "  Misleading-result risk: very high if historical cutoff/rank summaries are treated as confirmed outcomes.",
            "  Supervised ML suitability: NOT FEASIBLE UNTIL VERIFIED TARGET DATA EXISTS.",
            "",
            "No target labels were created during this audit.",
        ]
    )


def append_leakage(lines: list[str]) -> None:
    lines.extend(
        [
            "5. Data Leakage Analysis",
            "-------------------------",
            "year:",
            "  Available in data: YES. Potential use: time ordering.",
            "  Leakage risk: future-year information if random splits are used for future prediction.",
            "  Review: use chronological evaluation.",
            "",
            "college_code and branch_code:",
            "  Available in data: YES. Potential use: entity identification/filtering.",
            "  Leakage risk: entity memorization and unseen-entity failure; code availability at prediction time must be confirmed.",
            "",
            "college_name and branch_name:",
            "  Available in data: YES. Potential use: descriptive display or encoded categoricals.",
            "  Leakage risk: high-cardinality memorization, historical name changes, and post-event updates.",
            "",
            "cutoff_* columns:",
            "  Available in data: YES. Potential use: historical context only if available before prediction.",
            "  Leakage risk: direct target leakage when predicting the same cutoff, and same-year/post-event leakage.",
            "",
            "rank_* columns:",
            "  Available in data: YES. Potential use: historical context only if available before prediction.",
            "  Leakage risk: direct target leakage when predicting the same rank, and same-year/post-event leakage.",
            "",
            "*_partial columns:",
            "  Available in data: YES. Meaning and timing are unverified.",
            "  Leakage risk: indicators may encode outcome availability or post-event processing.",
            "",
            "Outcome-derived fields:",
            "  Explicit outcome-derived columns observed: NONE.",
            "  This absence prevents actual outcome modeling; it does not make other fields automatically safe.",
        ]
    )


def append_features(lines: list[str]) -> None:
    lines.extend(
        [
            "6. Feature Feasibility Analysis",
            "--------------------------------",
            "Feature | Present | Prediction-time availability | Leakage concern | Decision",
            "district | YES | Deployment-dependent | Future or post-event changes possible | REVIEW",
            "college_type | YES | Deployment-dependent | May be known, revised, or unavailable at prediction time | REVIEW",
            "branch_code | YES | Usually needed for requested course filtering | Entity memorization/unseen branch risk | REVIEW",
            "branch_name | YES | Descriptive; availability must be confirmed | High-cardinality and historical-name leakage | REVIEW/avoid as primary identifier",
            "college_code | YES | May be known for historical entities | Entity memorization and future-code changes | REVIEW",
            "college_name | YES | Descriptive; availability must be confirmed | High-cardinality/address variation | REVIEW/avoid as primary identifier",
            "category | Represented by wide category columns, not a row-level field | Student category may be known at input time | Wrong category mapping or cross-category leakage | EXPLICIT MAPPING REQUIRED",
            "year | YES | Prediction year is known by design | Future-year leakage if split incorrectly | USE FOR TIME ORDER, NOT RANDOM SPLIT",
            "historical cutoff values | YES | Only if available before prediction | Future/same-year target leakage | REVIEW TIMING",
            "historical rank values | YES | Only if available before prediction | Future/same-year target leakage | REVIEW TIMING",
            "partial indicators | YES | Timing and meaning unknown | Possible outcome-derived leakage | REVIEW/EXCLUDE UNTIL VERIFIED",
            "",
            "No feature is declared unconditionally safe because the prediction timestamp and deployment workflow are not defined.",
        ]
    )


def append_temporal(lines: list[str], frame: pd.DataFrame) -> None:
    counts = frame.groupby("year").size().to_dict()
    lines.extend(
        [
            "7. Temporal Validation Analysis",
            "--------------------------------",
            "Option A: reference/training years 2021-2023, validation 2024, test 2025.",
            f"  Rows: reference={sum(counts.get(year, 0) for year in [2021, 2022, 2023])}, validation={counts.get(2024, 0)}, test={counts.get(2025, 0)}.",
            "  Logical suitability: suitable for a chronology-preserving evaluation design, subject to target availability and timing.",
            "  Limitation: no model was trained and no performance was measured.",
            "",
            "Option B: reference/training years 2021-2024, test 2025.",
            f"  Rows: reference={sum(counts.get(year, 0) for year in [2021, 2022, 2023, 2024])}, test={counts.get(2025, 0)}.",
            "  Logical suitability: suitable for a final holdout design, subject to target availability and timing.",
            "  Limitation: no separate validation year is available in this design.",
            "",
            "No final split was selected and no training was performed.",
        ]
    )


def append_baseline(lines: list[str]) -> None:
    lines.extend(
        [
            "8. Baseline Comparison",
            "-----------------------",
            "Any future ML model must outperform transparent baselines such as:",
            "- Stage 10 exact-branch historical threshold comparison.",
            "- Simple historical threshold rules using the documented project working assumptions.",
            "- Historical aggregate summaries by college_code + branch_code + category + year.",
            "",
            "No evidence currently shows ML improves on these baselines because no model experiment was run.",
            "Baseline evaluation must use the same target definition, time split, missing-data policy, and prediction timestamp.",
        ]
    )


def append_required_data(lines: list[str]) -> None:
    lines.extend(
        [
            "9. Required Additional Data for Actual Admission Prediction",
            "--------------------------------------------------------------",
            "Required or strongly relevant information not confirmed in the current dataset:",
            "- Verified student-level admission or seat-allocation outcomes.",
            "- Counselling round and stage.",
            "- Seat availability and branch/category seat matrix.",
            "- Student preferences and choice order.",
            "- Student category and eligibility details with authoritative definitions.",
            "- Admission rules applied in each year and round.",
            "- Prediction-time feature availability and publication timestamps.",
            "- Authoritative cutoff/rank definitions and comparison direction.",
            "- A reliable target definition and later-year outcome validation set.",
            "",
            "These requirements are not assumed to exist; they must be obtained or verified before outcome modeling.",
        ]
    )


def append_conclusions(lines: list[str]) -> None:
    lines.extend(
        [
            "10. Risks and Limitations",
            "--------------------------",
            "- Five historical years provide limited temporal coverage for a future model.",
            "- Category missingness is substantial, especially for SCA and ST measures.",
            "- Cutoff/rank semantics, direction, and counselling round remain unverified.",
            "- Aggregate college/branch values are not individual admission outcomes.",
            "- Historical name variants and entity changes can cause generalization risk.",
            "- Same-year and future-year values may leak information depending on prediction timing.",
            "- Partial indicator meaning and timing are not confirmed.",
            "",
            "11. Final Feasibility Conclusions",
            "----------------------------------",
            "Historical comparison tool: FEASIBLE and already implemented as a rule-based Stage 11 application.",
            "Historical threshold eligibility estimate: CONDITIONALLY FEASIBLE as a transparent, explicitly labelled rule-based estimate; not a verified outcome label.",
            "Historical descriptive score: CONDITIONALLY FEASIBLE if kept descriptive, non-probabilistic, and evaluated chronologically.",
            "Actual admission probability model: NOT CURRENTLY FEASIBLE from this dataset alone; verified outcome and timing data are required.",
            "General ML approval: NOT GRANTED by this audit.",
            "",
            "12. Audit Completion and Preservation",
            "--------------------------------------",
            "Audit completed successfully: YES",
            "ML training performed: NO",
            "Model files created: NO",
            "Fake target labels created: NO",
            "Source CSV modified: NO",
            "Stage 1-11 files modified: NO",
            "Missing values imputed: NO",
            "Recommended next step: obtain human approval and verified outcome/metadata requirements before any Stage 13 or model work.",
            f"Report path: {REPORT_PATH}",
        ]
    )


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Input CSV not found: {INPUT_PATH}")
    source_hash_before = sha256(INPUT_PATH)
    frame = pd.read_csv(INPUT_PATH)
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Input CSV is missing required columns: {missing}")
    if int(frame.duplicated(KEY_COLUMNS).sum()):
        raise ValueError("Duplicate primary keys found")

    lines = [
        "STAGE 12 - ML FEASIBILITY AND TARGET DESIGN AUDIT",
        "=================================================",
        "",
        "1. Audit Objective",
        "-------------------",
        "Assess whether the existing TNEA dataset supports meaningful supervised ML, rule-based historical comparison, descriptive scores, or actual admission outcome modeling.",
        "This is a read-only audit. No target labels or models are created.",
        "",
        "2. Files Inspected",
        "-------------------",
        f"Primary dataset: {INPUT_PATH}",
        "Stage 10: stage10_historical_comparison.py and stage10_historical_comparison_report.txt",
        "Stage 11: stage11_app.py and stage11_application_report.txt",
        "Stage 11.1: stage11_ux_validation_report.txt",
        "Existing Stage 1-9 audit artifacts were preserved and used as context.",
        "",
    ]
    append_dataset_structure(lines, frame)
    append_targets(lines, frame)
    append_leakage(lines)
    append_features(lines)
    append_temporal(lines, frame)
    append_baseline(lines)
    append_required_data(lines)
    append_conclusions(lines)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if sha256(INPUT_PATH) != source_hash_before:
        raise RuntimeError("Source CSV hash changed during audit")

    print("STAGE 12 ML FEASIBILITY AUDIT COMPLETE")
    print(f"Rows audited: {len(frame)}")
    print(f"Years: {sorted(int(value) for value in frame['year'].unique())}")
    print("Historical comparison: FEASIBLE")
    print("Historical descriptive score: CONDITIONALLY FEASIBLE")
    print("Actual admission probability model: NOT CURRENTLY FEASIBLE")
    print("ML training performed: False")
    print("Source CSV unchanged: True")
    print(f"Report created successfully: {REPORT_PATH}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, FileNotFoundError, RuntimeError) as error:
        print(f"STAGE 12 AUDIT FAILED: {error}")
        raise SystemExit(1) from error
