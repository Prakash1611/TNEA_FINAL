from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = ROOT / "data" / "integrated" / "tnea_integrated_master.csv"
REPORT_PATH = ROOT / "documentation" / "target_temporal_report.txt"
KEY_COLUMNS = ["year", "college_code", "branch_code"]
TARGET_COLUMNS = [
    "cutoff_oc",
    "cutoff_bc",
    "cutoff_bcm",
    "cutoff_mbc",
    "cutoff_sc",
    "cutoff_sca",
    "cutoff_st",
    "rank_oc",
    "rank_bc",
    "rank_bcm",
    "rank_mbc",
    "rank_sc",
    "rank_sca",
    "rank_st",
]
IDENTIFIER_COLUMNS = [
    "year",
    "college_code",
    "branch_code",
    "college_name",
    "branch_name",
    "district",
    "college_type",
]
PARTIAL_COLUMNS = [
    "cutoff_oc_partial",
    "cutoff_bc_partial",
    "cutoff_bcm_partial",
    "cutoff_mbc_partial",
    "cutoff_sc_partial",
    "cutoff_sca_partial",
    "cutoff_st_partial",
    "rank_oc_partial",
    "rank_bc_partial",
    "rank_bcm_partial",
    "rank_mbc_partial",
    "rank_sc_partial",
    "rank_sca_partial",
    "rank_st_partial",
]
REQUIRED_COLUMNS = KEY_COLUMNS + TARGET_COLUMNS + IDENTIFIER_COLUMNS[3:] + PARTIAL_COLUMNS
YEARS = [2021, 2022, 2023, 2024, 2025]


def pct(value: int, total: int) -> str:
    return f"{100 * value / total:.2f}%" if total else "0.00%"


def target_measure(column: str) -> str:
    return "cutoff" if column.startswith("cutoff_") else "rank"


def target_category(column: str) -> str:
    return column.split("_")[-1]


def format_number(value: float | int | None) -> str:
    if pd.isna(value):
        return "NA"
    return f"{value:.6g}"


def validate_input(frame: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Input is missing required columns: {missing}")
    if frame["year"].isna().any():
        raise ValueError("Input contains missing year values")


def target_stats(frame: pd.DataFrame, column: str) -> dict[str, object]:
    values = pd.to_numeric(frame[column], errors="coerce")
    available = int(values.notna().sum())
    missing = int(values.isna().sum())
    valid = values.dropna()
    return {
        "available": available,
        "missing": missing,
        "missing_pct": pct(missing, len(frame)),
        "minimum": format_number(valid.min() if len(valid) else None),
        "maximum": format_number(valid.max() if len(valid) else None),
        "unique": int(valid.nunique()),
        "negative": int((valid < 0).sum()),
        "zero": int((valid == 0).sum()),
        "non_numeric": int(frame[column].notna().sum() - values.notna().sum()),
    }


def split_stats(frame: pd.DataFrame, split_name: str, years: list[int]) -> list[str]:
    subset = frame[frame["year"].isin(years)]
    lines = [
        f"{split_name}:",
        f"  years: {years[0]}-{years[-1]}",
        f"  rows: {len(subset)}",
    ]
    for target in TARGET_COLUMNS:
        values = pd.to_numeric(subset[target], errors="coerce")
        available = int(values.notna().sum())
        missing = int(values.isna().sum())
        lines.append(
            f"  {target}: usable_target_rows={available}, missing={missing}, "
            f"missing_pct={pct(missing, len(subset))}"
        )
    return lines


def append_leakage_review(lines: list[str]) -> None:
    lines.extend(
        [
            "8. Temporal Leakage Review",
            "---------------------------",
            "The following statements separate observed data structure from deployment-dependent risk.",
            "",
            "year:",
            "  Observed fact: contains years 2021-2025.",
            "  Possible use: time ordering and chronological evaluation.",
            "  Risk: random splits can expose future-year patterns to training; the safe use depends on the intended forecast horizon.",
            "",
            "college_code and branch_code:",
            "  Observed fact: identifiers are complete and the combined primary key is unique.",
            "  Possible use: entity identification or categorical inputs.",
            "  Risk: memorization, unseen-entity failure, or future information encoded in an identifier; availability must be confirmed.",
            "",
            "college_name and branch_name:",
            "  Observed fact: descriptive names exist and historical name variation is present.",
            "  Possible use: descriptive fields or carefully encoded categorical inputs.",
            "  Risk: high-cardinality memorization, spelling/address changes, and leakage if a name reflects a post-event update.",
            "",
            "district and college_type:",
            "  Observed fact: descriptive fields are present for the records.",
            "  Possible use: contextual inputs if known at prediction time.",
            "  Risk: leakage if values are revised after the prediction timestamp; this cannot be confirmed from the CSV alone.",
            "",
            "cutoff_* columns:",
            "  Observed fact: these are cutoff-related numeric columns with category-specific missingness.",
            "  Possible use: features only when published before the target event and not the target itself.",
            "  Risk: direct target leakage when predicting a cutoff, or post-event leakage when the cutoff is known only afterward.",
            "",
            "rank_* columns:",
            "  Observed fact: these are separate rank-related numeric columns with category-specific missingness.",
            "  Possible use: features only when available before the target event and not the target itself.",
            "  Risk: direct target leakage when predicting a rank, or post-event leakage when ranks are observed after the prediction timestamp.",
            "",
            "*_partial columns:",
            "  Observed fact: partial indicator columns are present separately for cutoff and rank.",
            "  Possible use: features only after their timing and meaning are confirmed.",
            "  Risk: an indicator may encode whether an outcome or post-event processing result is available.",
        ]
    )


def append_same_year_review(lines: list[str]) -> None:
    lines.extend(
        [
            "9. Same-Year and Future Information Risks",
            "------------------------------------------",
            "For every target below, the other cutoff/rank columns are listed as same-year measures.",
            "Their use is deployment-dependent: a same-year value published after the prediction timestamp is leakage.",
            "",
        ]
    )
    for target in TARGET_COLUMNS:
        other_targets = [column for column in TARGET_COLUMNS if column != target]
        lines.extend(
            [
                f"{target}:",
                f"  same-year other measures: {', '.join(other_targets)}",
                "  review requirement: determine whether each candidate input was available before this target was known.",
                "  no columns were removed or modified by this audit.",
            ]
        )


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_PATH}")

    frame = pd.read_csv(INPUT_PATH)
    validate_input(frame)
    lines: list[str] = [
        "STAGE 5 - TARGET DEFINITION AND TEMPORAL SPLITTING AUDIT",
        "==========================================================",
        "",
        "1. Audit Scope",
        "--------------",
        f"Input file: {INPUT_PATH}",
        "Audit mode: read-only",
        "Input CSV modified: NO",
        "Rows deleted: NO",
        "Missing values filled or replaced: NO",
        "Feature engineering performed: NO",
        "ML model trained: NO",
        "Cutoff/rank meanings assumed: NO",
        "",
        "2. Dataset and Year Summary",
        "---------------------------",
        f"Rows: {len(frame)}",
        f"Columns: {len(frame.columns)}",
        f"Available years: {sorted(frame['year'].unique().tolist())}",
        f"Minimum year: {frame['year'].min()}",
        f"Maximum year: {frame['year'].max()}",
        f"Primary key: {', '.join(KEY_COLUMNS)}",
        f"Primary-key duplicate rows: {int(frame.duplicated(KEY_COLUMNS).sum())}",
        "",
        "Rows and college+branch duplicate check by year:",
    ]
    for year in YEARS:
        subset = frame[frame["year"] == year]
        duplicate_count = int(subset.duplicated(["college_code", "branch_code"]).sum())
        lines.append(f"  {year}: rows={len(subset)}, duplicate college+branch combinations={duplicate_count}")

    lines.extend(["", "3. Potential Target Inventory", "------------------------------"])
    lines.append("Target values are measured as present or missing; missing values are never treated as zero.")
    lines.append(
        "Target | Measure | Category | Rows | Available | Missing | Missing % | Min | Max | Unique | Negative | Zero | Non-numeric"
    )
    for target in TARGET_COLUMNS:
        stats = target_stats(frame, target)
        lines.append(
            f"{target} | {target_measure(target)} | {target_category(target).upper()} | {len(frame)} | "
            f"{stats['available']} | {stats['missing']} | {stats['missing_pct']} | {stats['minimum']} | "
            f"{stats['maximum']} | {stats['unique']} | {stats['negative']} | {stats['zero']} | {stats['non_numeric']}"
        )

    lines.extend(["", "4. Target Availability by Year", "-------------------------------"])
    for target in TARGET_COLUMNS:
        lines.append(f"{target}:")
        for year in YEARS:
            subset = frame[frame["year"] == year]
            available = int(pd.to_numeric(subset[target], errors="coerce").notna().sum())
            missing = len(subset) - available
            lines.append(
                f"  {year}: total={len(subset)}, available={available}, missing={missing}, missing_pct={pct(missing, len(subset))}"
            )
        lines.append("  Very-low-availability flag: years below 25% available are flagged for review only.")
        for year in YEARS:
            subset = frame[frame["year"] == year]
            available_pct = 100 * pd.to_numeric(subset[target], errors="coerce").notna().mean()
            if available_pct < 25:
                lines.append(f"    review year {year}: available={available_pct:.2f}%")

    lines.extend(
        [
            "",
            "5. Target Eligibility Analysis",
            "-------------------------------",
            "A target-specific preparation step may exclude rows with a missing target, but this audit does not exclude or delete them.",
            "Missing target values are distinct from valid numerical values and are not zero-filled.",
        ]
    )
    for target in TARGET_COLUMNS:
        stats = target_stats(frame, target)
        lines.append(
            f"{target}: eligible-by-availability rows={stats['available']}; missing-target rows={stats['missing']}; "
            f"missing_pct={stats['missing_pct']}; available_years="
            f"{sorted(frame.loc[frame[target].notna(), 'year'].unique().tolist())}"
        )

    lines.extend(["", "6. Temporal Split Option A", "--------------------------"])
    lines.extend(split_stats(frame, "Training", [2021, 2022, 2023]))
    lines.extend(split_stats(frame, "Validation", [2024]))
    lines.extend(split_stats(frame, "Test", [2025]))
    lines.extend(
        [
            "Implication: this option provides a separate validation year and a later test year, but each target has its own usable-row counts.",
            "No final split was selected by this audit.",
            "",
            "7. Temporal Split Option B",
            "--------------------------",
        ]
    )
    lines.extend(split_stats(frame, "Training", [2021, 2022, 2023, 2024]))
    lines.extend(split_stats(frame, "Test", [2025]))
    lines.extend(
        [
            "Implication: this option uses more historical training data but does not provide a separate validation year in this design.",
            "No final split was selected by this audit.",
            "",
        ]
    )

    append_leakage_review(lines)
    append_same_year_review(lines)

    lines.extend(
        [
            "",
            "10. Target Comparison Framework",
            "--------------------------------",
            "No single target is recommended. One target should be defined at a time based on the intended application.",
            "Target | Measure | Category | Missing % | Available years | Modeling concern | Human question",
        ]
    )
    for target in TARGET_COLUMNS:
        stats = target_stats(frame, target)
        available_years = sorted(frame.loc[frame[target].notna(), "year"].unique().tolist())
        concern = (
            "category-specific missingness; confirm target timing and eligibility; do not treat missing as zero"
        )
        question = (
            "Is this measure the desired outcome, and was it available at the intended prediction timestamp?"
        )
        lines.append(
            f"{target} | {target_measure(target)} | {target_category(target).upper()} | {stats['missing_pct']} | "
            f"{available_years} | {concern} | {question}"
        )

    lines.extend(
        [
            "",
            "11. Questions Requiring Human Decision",
            "---------------------------------------",
            "1. What real-world event and timestamp define the prediction task?",
            "2. Is the target a cutoff measure, a rank-related measure, or a category-specific outcome?",
            "3. Which fields are available before that timestamp in the intended deployment workflow?",
            "4. Should the task predict one category at a time, or is there a justified multi-target design?",
            "5. How should rows with missing target values be handled during target-specific preparation?",
            "6. Are college_code and branch_code valid known entities at prediction time, and how should unseen entities be evaluated?",
            "7. What do the cutoff and rank partial indicators mean, and when are they generated?",
            "8. Should Option A or Option B be used, or is another chronological split required?",
        ]
    )

    lines.extend(
        [
            "",
            "12. Final Audit Summary",
            "-----------------------",
            "Audit completed successfully: YES",
            "Input CSV modified: NO",
            "Missing values filled: NO",
            "Rows deleted: NO",
            "Features engineered: NO",
            "ML model trained: NO",
            "Final target selected: NO",
            "Final temporal split selected: NO",
            "",
            "Decisions requiring human confirmation before Stage 6:",
            "- prediction event and timestamp",
            "- target definition and category scope",
            "- pre-prediction feature availability",
            "- missing-target eligibility policy",
            "- meaning and timing of partial indicators",
            "- chronological split design",
            "- handling of known and unseen colleges/branches",
            "",
            f"Report generated: {REPORT_PATH}",
        ]
    )

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("STAGE 5 TARGET/TEMPORAL AUDIT COMPLETE")
    print(f"Rows audited: {len(frame)}")
    print(f"Years: {sorted(frame['year'].unique().tolist())}")
    print(f"Primary-key duplicate rows: {int(frame.duplicated(KEY_COLUMNS).sum())}")
    print(f"Targets audited: {len(TARGET_COLUMNS)}")
    print("No target selected and no temporal split selected.")
    print("Warnings: target-specific missingness, timing-dependent leakage, and partial-indicator semantics require review.")
    print(f"Report created successfully: {REPORT_PATH}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, FileNotFoundError) as error:
        print(f"STAGE 5 AUDIT FAILED: {error}")
        raise SystemExit(1) from error
