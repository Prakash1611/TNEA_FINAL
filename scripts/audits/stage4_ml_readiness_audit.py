from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = ROOT / "data" / "integrated" / "tnea_integrated_master.csv"
REPORT_PATH = ROOT / "documentation" / "ml_readiness_report.txt"
KEY_COLUMNS = ["year", "college_code", "branch_code"]
CATEGORIES = ["oc", "bc", "bcm", "mbc", "sc", "sca", "st"]
CUTOFF_COLUMNS = [f"cutoff_{category}" for category in CATEGORIES]
RANK_COLUMNS = [f"rank_{category}" for category in CATEGORIES]
CUTOFF_PARTIAL_COLUMNS = [f"cutoff_{category}_partial" for category in CATEGORIES]
RANK_PARTIAL_COLUMNS = [f"rank_{category}_partial" for category in CATEGORIES]
MEASURE_COLUMNS = CUTOFF_COLUMNS + RANK_COLUMNS
PARTIAL_COLUMNS = CUTOFF_PARTIAL_COLUMNS + RANK_PARTIAL_COLUMNS
EXTREME_VALUE_THRESHOLD = 1_000_000
HIGH_MISSINGNESS_THRESHOLD = 0.50


def percent(value: int, total: int) -> str:
    return f"{(100 * value / total):.2f}%" if total else "0.00%"


def values_text(values: list[object], limit: int = 12) -> str:
    shown = [str(value) for value in values[:limit]]
    suffix = " ..." if len(values) > limit else ""
    return ", ".join(shown) + suffix


def count_table(series: pd.Series) -> str:
    counts = series.value_counts(dropna=False).to_dict()
    return ", ".join(f"{key}: {value}" for key, value in counts.items())


def append_distribution(lines: list[str], label: str, counts: pd.Series) -> None:
    lines.append(label)
    lines.append(f"  count: {int(counts.count())}")
    lines.append(f"  min: {counts.min():.2f}")
    lines.append(f"  max: {counts.max():.2f}")
    lines.append(f"  mean: {counts.mean():.2f}")
    lines.append(f"  median: {counts.median():.2f}")
    lines.append(f"  p05: {counts.quantile(0.05):.2f}")
    lines.append(f"  p95: {counts.quantile(0.95):.2f}")


def audit() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_PATH}")

    frame = pd.read_csv(INPUT_PATH)
    total_rows = len(frame)
    lines: list[str] = [
        "TNEA STAGE 4 - ML READINESS AND DATA QUALITY AUDIT",
        "===================================================",
        "",
        "AUDIT SCOPE",
        "-----------",
        f"Input file: {INPUT_PATH}",
        "Read-only audit: YES",
        "CSV values modified: NO",
        "Rows deleted: NO",
        "Missing values filled: NO",
        "Feature engineering performed: NO",
        "ML model trained: NO",
        "",
        "1. DATASET SUMMARY",
        "------------------",
        f"Rows: {total_rows}",
        f"Columns: {len(frame.columns)}",
        f"Exact duplicate rows: {int(frame.duplicated().sum())}",
        f"Duplicate ({', '.join(KEY_COLUMNS)}) rows: {int(frame.duplicated(KEY_COLUMNS).sum())}",
        f"Memory usage (deep): {int(frame.memory_usage(deep=True).sum()):,} bytes",
        f"Memory usage (deep): {frame.memory_usage(deep=True).sum() / (1024 ** 2):.2f} MiB",
        "",
        "Column data types:",
    ]
    lines.extend(f"  {column}: {dtype}" for column, dtype in frame.dtypes.items())

    lines.extend(["", "2. MISSING-VALUE ANALYSIS", "--------------------------"])
    lines.append("Missing counts, percentages, and available counts by column:")
    for column in frame.columns:
        missing = int(frame[column].isna().sum())
        lines.append(
            f"  {column}: missing={missing}, missing_pct={percent(missing, total_rows)}, "
            f"available={total_rows - missing}"
        )
    lines.extend(["", "Category measure missingness:"])
    for column in MEASURE_COLUMNS:
        missing = int(frame[column].isna().sum())
        lines.append(
            f"  {column}: missing={missing}, missing_pct={percent(missing, total_rows)}, "
            f"available={total_rows - missing}"
        )

    lines.extend(
        [
            "",
            "3. NUMERICAL VALIDATION",
            "------------------------",
            f"Extremely large threshold: > {EXTREME_VALUE_THRESHOLD:,}",
            "No values are modified or removed; all flags require manual review.",
        ]
    )
    suspicious_measure_count = 0
    for column in MEASURE_COLUMNS:
        numeric = pd.to_numeric(frame[column], errors="coerce")
        non_numeric = int(frame[column].notna().sum() - numeric.notna().sum())
        valid = numeric.dropna()
        zero_count = int((valid == 0).sum())
        negative_count = int((valid < 0).sum())
        extreme_count = int((valid > EXTREME_VALUE_THRESHOLD).sum())
        suspicious = zero_count + negative_count + extreme_count + non_numeric
        suspicious_measure_count += suspicious
        if len(valid):
            minimum = f"{valid.min():.6g}"
            maximum = f"{valid.max():.6g}"
            mean = f"{valid.mean():.6g}"
            median = f"{valid.median():.6g}"
        else:
            minimum = maximum = mean = median = "NA"
        lines.extend(
            [
                f"{column}:",
                f"  min={minimum}, max={maximum}, mean={mean}, median={median}",
                f"  zeros={zero_count}, negatives={negative_count}, extremely_large={extreme_count}, non_numeric={non_numeric}",
                f"  suspicious_for_manual_review={'YES' if suspicious else 'NO'}",
            ]
        )

    lines.extend(["", "4. YEAR-WISE ANALYSIS", "----------------------"])
    year_values = sorted(frame["year"].dropna().unique().tolist())
    lines.append(f"Years present: {values_text(year_values)}")
    for year in year_values:
        subset = frame[frame["year"] == year]
        lines.extend(["", f"Year {year}: total_records={len(subset)}"])
        lines.append("  Available cutoff values:")
        lines.extend(f"    {column}: {int(subset[column].notna().sum())}" for column in CUTOFF_COLUMNS)
        lines.append("  Available rank values:")
        lines.extend(f"    {column}: {int(subset[column].notna().sum())}" for column in RANK_COLUMNS)
        lines.append("  Missing cutoff values:")
        lines.extend(f"    {column}: {int(subset[column].isna().sum())}" for column in CUTOFF_COLUMNS)
        lines.append("  Missing rank values:")
        lines.extend(f"    {column}: {int(subset[column].isna().sum())}" for column in RANK_COLUMNS)
        lines.append("  Partial indicator counts (value 1):")
        lines.extend(f"    {column}: {int((subset[column] == 1).sum())}" for column in PARTIAL_COLUMNS)

    lines.extend(["", "5. COLLEGE AND BRANCH ANALYSIS", "------------------------------"])
    college_counts = frame.groupby("college_code").size()
    branch_counts = frame.groupby("branch_code").size()
    college_low = college_counts[college_counts < 5]
    college_high = college_counts[college_counts >= college_counts.quantile(0.95)]
    branch_low = branch_counts[branch_counts < 5]
    branch_high = branch_counts[branch_counts >= branch_counts.quantile(0.95)]
    lines.extend(
        [
            f"Unique colleges by college_code: {frame['college_code'].nunique()}",
            f"Unique branches by branch_code: {frame['branch_code'].nunique()}",
            "",
        ]
    )
    append_distribution(lines, "Records per college_code:", college_counts)
    lines.append(f"  unusually few (<5 records): {len(college_low)} codes: {values_text(college_low.index.tolist())}")
    lines.append(
        f"  unusually many (>=95th percentile, threshold {college_counts.quantile(0.95):.2f}): "
        f"{len(college_high)} codes: {values_text(college_high.index.tolist())}"
    )
    lines.append("")
    append_distribution(lines, "Records per branch_code:", branch_counts)
    lines.append(f"  unusually few (<5 records): {len(branch_low)} codes: {values_text(branch_low.index.tolist())}")
    lines.append(
        f"  unusually many (>=95th percentile, threshold {branch_counts.quantile(0.95):.2f}): "
        f"{len(branch_high)} codes: {values_text(branch_high.index.tolist())}"
    )

    college_name_changes = frame.groupby("college_code")["college_name"].nunique()
    branch_name_changes = frame.groupby("branch_code")["branch_name"].nunique()
    college_changes = college_name_changes[college_name_changes > 1]
    branch_changes = branch_name_changes[branch_name_changes > 1]
    lines.extend(
        [
            "",
            f"Historical college-name changes by college_code: {len(college_changes)} codes",
        ]
    )
    for code in college_changes.index:
        names = sorted(frame.loc[frame["college_code"] == code, "college_name"].dropna().unique().tolist())
        lines.append(f"  college_code={code}: {values_text(names, limit=20)}")
    lines.append(f"Historical branch-name changes by branch_code: {len(branch_changes)} codes")
    for code in branch_changes.index:
        names = sorted(frame.loc[frame["branch_code"] == code, "branch_name"].dropna().unique().tolist())
        lines.append(f"  branch_code={code}: {values_text(names, limit=20)}")
    lines.append("Names are descriptive fields; college_code and branch_code remain the identifiers.")

    lines.extend(["", "6. PARTIAL INDICATOR VALIDATION", "--------------------------------"])
    lines.append("Combinations are reported without assuming that partial=1 has identical semantics across sources.")
    potential_partial_reviews = 0
    for source, value_columns, indicator_columns in [
        ("cutoff", CUTOFF_COLUMNS, CUTOFF_PARTIAL_COLUMNS),
        ("rank", RANK_COLUMNS, RANK_PARTIAL_COLUMNS),
    ]:
        lines.append(f"{source.upper()} indicators:")
        for category, value_column, indicator_column in zip(CATEGORIES, value_columns, indicator_columns):
            value_missing = frame[value_column].isna()
            indicator = frame[indicator_column]
            invalid_indicator = int((~indicator.isin([0, 1])).sum())
            combinations = {
                "value_missing_indicator_0": int((value_missing & (indicator == 0)).sum()),
                "value_missing_indicator_1": int((value_missing & (indicator == 1)).sum()),
                "value_present_indicator_0": int((~value_missing & (indicator == 0)).sum()),
                "value_present_indicator_1": int((~value_missing & (indicator == 1)).sum()),
            }
            review_count = combinations["value_missing_indicator_0"] + combinations["value_present_indicator_1"]
            potential_partial_reviews += review_count + invalid_indicator
            lines.append(
                f"  {category}: {indicator_column} invalid={invalid_indicator}; "
                f"{count_table(pd.Series(combinations))}; convention-dependent_review_combinations={review_count}"
            )
    lines.append(
        f"Total convention-dependent partial combinations requiring semantic review: {potential_partial_reviews}. "
        "These were not changed."
    )

    lines.extend(
        [
            "",
            "7. CUTOFF AND RANK ANALYSIS",
            "----------------------------",
            "Cutoff columns are treated as cutoff marks. Rank columns are treated as a separate rank-related measure.",
            "No numerical comparison between cutoff and rank values was used as a quality rule.",
            "No cutoff or rank values were merged, overwritten, coalesced, or imputed.",
            f"Cutoff columns audited: {', '.join(CUTOFF_COLUMNS)}",
            f"Rank columns audited: {', '.join(RANK_COLUMNS)}",
        ]
    )

    lines.extend(
        [
            "",
            "8. DATA LEAKAGE ANALYSIS",
            "-------------------------",
            "The following is a pre-modeling risk assessment, not a trained-model result.",
            "",
            "year:",
            "  Safe use: time ordering and train/test split control.",
            "  Leakage risk: using future-year records or random splits when evaluating future-year predictions.",
            "",
            "college_code and branch_code:",
            "  Safe use: identifiers or categorical entities when the deployment setting permits known entities.",
            "  Leakage risk: memorization of entities, unseen-entity generalization failure, or use of codes that encode future information.",
            "",
            "cutoff values:",
            "  Potential feature when predicting a later outcome and the cutoff is available before prediction.",
            "  Leakage risk: direct target leakage if predicting the same cutoff value, or if the cutoff is published only after the prediction point.",
            "",
            "rank values:",
            "  Potential feature only when rank is available at prediction time and is not the target or a direct derivative of it.",
            "  Leakage risk: direct leakage if predicting the same rank-related measure or using a value observed after the target event.",
            "",
            "partial indicators:",
            "  Potential feature describing availability or partial status, subject to confirming its timing and meaning.",
            "  Leakage risk: the indicator may encode outcome availability or post-event processing.",
            "",
            "college_name and branch_name:",
            "  Safe use: descriptive display fields or carefully encoded categorical variables.",
            "  Leakage risk: high-cardinality memorization and historical spelling/address changes; do not use as primary identifiers.",
        ]
    )

    lines.extend(
        [
            "",
            "9. POTENTIAL ML TARGETS",
            "------------------------",
            "No model was trained and no target was created.",
            "",
            "A. Cutoff prediction",
            "  Candidate target: one cutoff_* column for a specified category.",
            "  Possible inputs: year, college_code, branch_code, verified historical data, and rank_* only if available before prediction.",
            "  Missing concern: category-specific missing values are common; do not treat them as zero.",
            "  Split requirement: train on earlier years and validate on a later held-out year.",
            "  Leakage risk: using the target cutoff itself, same-year post-outcome fields, or rank data that is unavailable at prediction time.",
            "",
            "B. Rank prediction",
            "  Candidate target: one rank_* column for a specified category.",
            "  Possible inputs: year, college_code, branch_code, historical cutoff_* values only when temporally available.",
            "  Missing concern: rank missingness varies by category and must remain missing during audit/preparation.",
            "  Split requirement: use an earlier-year to later-year time split.",
            "  Leakage risk: using the target rank itself, same-event cutoff data, or post-event partial indicators.",
            "",
            "C. Category-specific prediction",
            "  Candidate target: one category-specific cutoff or rank column at a time.",
            "  Possible inputs: identifiers, year, and only pre-outcome variables justified by the deployment timeline.",
            "  Missing concern: target availability is category-specific; define the eligible population before modeling.",
            "  Split requirement: preserve chronology and test on a later year.",
            "  Leakage risk: mixing cutoff and rank measures without a time definition or using a target-derived indicator.",
        ]
    )

    lines.extend(["", "10. CONSTANT AND NEAR-CONSTANT COLUMNS", "----------------------------------------"])
    constant_columns = []
    near_constant_columns = []
    high_missing_columns = []
    for column in frame.columns:
        unique_count = int(frame[column].nunique(dropna=False))
        dominant_fraction = float(frame[column].value_counts(dropna=False, normalize=True).iloc[0])
        missing_fraction = float(frame[column].isna().mean())
        if unique_count == 1:
            constant_columns.append(column)
        if dominant_fraction >= 0.99:
            near_constant_columns.append(f"{column} (dominant={dominant_fraction:.2%})")
        if missing_fraction >= HIGH_MISSINGNESS_THRESHOLD:
            high_missing_columns.append(f"{column} ({missing_fraction:.2%} missing)")
    lines.append(f"Constant columns (one value including missing as a value): {constant_columns or 'None'}")
    lines.append(f"Near-constant columns (dominant value >=99%): {near_constant_columns or 'None'}")
    lines.append(f"Very high missingness (>=50%): {high_missing_columns or 'None'}")

    critical_warnings = []
    if int(frame.duplicated().sum()):
        critical_warnings.append("Duplicate rows exist.")
    if int(frame.duplicated(KEY_COLUMNS).sum()):
        critical_warnings.append("Duplicate identifier keys exist.")
    if suspicious_measure_count:
        critical_warnings.append(f"{suspicious_measure_count} numerical review flags were found; values were preserved.")
    if high_missing_columns:
        critical_warnings.append("Several category columns have at least 50% missing values.")
    if potential_partial_reviews:
        critical_warnings.append("Partial-indicator/value combinations require semantic review; no assumptions were applied.")
    critical_warnings.extend(
        [
            "Cutoff and rank columns are distinct measures and must not be used interchangeably.",
            "Random train/test splitting may leak temporal information; use a time-based split.",
        ]
    )
    lines.extend(["", "11. CRITICAL WARNINGS", "----------------------"])
    lines.extend(f"- {warning}" for warning in critical_warnings)

    lines.extend(
        [
            "",
            "12. RECOMMENDED NEXT STEPS",
            "---------------------------",
            "1. Confirm the deployment timestamp and define which fields are available before the prediction event.",
            "2. Resolve the semantic meaning of cutoff/rank partial indicators and the intended treatment of missing target values.",
            "3. Select one target definition at a time and build an eligibility rule without filling missing values as zero.",
            "4. Use a chronological train/validation/test design, with a later year held out for evaluation.",
            "5. Review high-missingness categories and entity generalization before any model training.",
            "",
            "AUDIT STATUS",
            "------------",
            "Stage 4 audit completed successfully.",
            "Source CSV modified: NO",
            "Integrated CSV modified: NO",
            f"Report generated: {REPORT_PATH}",
        ]
    )

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("STAGE 4 ML READINESS AUDIT COMPLETE")
    print(f"Rows audited: {total_rows}")
    print(f"Columns audited: {len(frame.columns)}")
    print(f"Duplicate rows: {int(frame.duplicated().sum())}")
    print(f"Duplicate keys: {int(frame.duplicated(KEY_COLUMNS).sum())}")
    print(f"Numerical review flags: {suspicious_measure_count}")
    print(f"High-missingness columns: {len(high_missing_columns)}")
    print("Leakage risks: temporal leakage, target leakage, availability timing, and entity memorization")
    print("Recommended next step: confirm prediction-time availability and target eligibility before modeling")
    print(f"Report created successfully: {REPORT_PATH}")


if __name__ == "__main__":
    try:
        audit()
    except (OSError, ValueError, KeyError, FileNotFoundError) as error:
        print(f"STAGE 4 AUDIT FAILED: {error}")
        raise SystemExit(1) from error
