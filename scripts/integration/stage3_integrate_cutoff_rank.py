from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
CUTOFF_PATH = ROOT / "data" / "cleaned" / "cutoff" / "tnea_cutoff_master_final.csv"
RANK_PATH = ROOT / "data" / "cleaned" / "rank" / "tnea_rank_master_final.csv"
OUTPUT_PATH = ROOT / "data" / "integrated" / "tnea_integrated_master.csv"
REPORT_PATH = ROOT / "documentation" / "integration_report.txt"

EXPECTED_ROWS = 16_174
KEY_COLUMNS = ["year", "college_code", "branch_code"]
IDENTIFIER_COLUMNS = [
    "year",
    "college_code",
    "college_name",
    "district",
    "college_type",
    "branch_code",
    "branch_name",
]
CATEGORY_COLUMNS = ["oc", "bc", "bcm", "mbc", "sc", "sca", "st"]
PARTIAL_COLUMNS = [f"{column}_partial" for column in CATEGORY_COLUMNS]
REQUIRED_COLUMNS = IDENTIFIER_COLUMNS + CATEGORY_COLUMNS + PARTIAL_COLUMNS


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fail(message: str) -> None:
    raise RuntimeError(f"STAGE 3 VALIDATION FAILED: {message}")


def assert_required_columns(frame: pd.DataFrame, label: str) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        fail(f"{label} is missing required columns: {missing}")


def key_frame(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[KEY_COLUMNS].copy()


def key_set(frame: pd.DataFrame) -> set[tuple[object, ...]]:
    return set(map(tuple, frame[KEY_COLUMNS].itertuples(index=False, name=None)))


def duplicate_key_count(frame: pd.DataFrame) -> int:
    return int(frame.duplicated(KEY_COLUMNS).sum())


def identifier_conflicts(cutoff: pd.DataFrame, rank: pd.DataFrame) -> dict[str, int]:
    non_key_identifiers = [column for column in IDENTIFIER_COLUMNS if column not in KEY_COLUMNS]
    left = cutoff[KEY_COLUMNS + non_key_identifiers].copy()
    right = rank[KEY_COLUMNS + non_key_identifiers].copy()
    comparison = left.merge(right, on=KEY_COLUMNS, suffixes=("_cutoff", "_rank"), validate="one_to_one")
    conflicts = {}
    for column in non_key_identifiers:
        conflicts[column] = int(
            (comparison[f"{column}_cutoff"] != comparison[f"{column}_rank"]).sum()
        )
    fatal_conflicts = {
        column: count
        for column, count in conflicts.items()
        if column != "branch_name" and count
    }
    if fatal_conflicts:
        fail(f"identifying-column conflicts found: {fatal_conflicts}")
    return conflicts


def main() -> None:
    if not CUTOFF_PATH.exists():
        fail(f"cutoff source file not found: {CUTOFF_PATH}")
    if not RANK_PATH.exists():
        fail(f"rank source file not found: {RANK_PATH}")

    cutoff_hash_before = file_hash(CUTOFF_PATH)
    rank_hash_before = file_hash(RANK_PATH)

    cutoff = pd.read_csv(CUTOFF_PATH)
    rank = pd.read_csv(RANK_PATH)

    assert_required_columns(cutoff, "cutoff dataset")
    assert_required_columns(rank, "rank dataset")

    cutoff_duplicates = duplicate_key_count(cutoff)
    rank_duplicates = duplicate_key_count(rank)
    if cutoff_duplicates:
        fail(f"cutoff dataset has {cutoff_duplicates} duplicate join-key rows")
    if rank_duplicates:
        fail(f"rank dataset has {rank_duplicates} duplicate join-key rows")

    cutoff_keys = key_set(cutoff)
    rank_keys = key_set(rank)
    unmatched_cutoff_keys = cutoff_keys - rank_keys
    unmatched_rank_keys = rank_keys - cutoff_keys
    if unmatched_cutoff_keys or unmatched_rank_keys:
        fail(
            "join-key sets do not match: "
            f"{len(unmatched_cutoff_keys)} cutoff-only and "
            f"{len(unmatched_rank_keys)} rank-only keys"
        )

    conflicts = identifier_conflicts(cutoff, rank)

    cutoff_values = cutoff[KEY_COLUMNS + CATEGORY_COLUMNS + PARTIAL_COLUMNS].rename(
        columns={
            **{column: f"cutoff_{column}" for column in CATEGORY_COLUMNS},
            **{column: f"cutoff_{column}" for column in PARTIAL_COLUMNS},
        }
    )
    rank_values = rank[KEY_COLUMNS + CATEGORY_COLUMNS + PARTIAL_COLUMNS].rename(
        columns={
            **{column: f"rank_{column}" for column in CATEGORY_COLUMNS},
            **{column: f"rank_{column}" for column in PARTIAL_COLUMNS},
        }
    )

    integrated = cutoff[IDENTIFIER_COLUMNS].merge(
        cutoff_values,
        on=KEY_COLUMNS,
        how="left",
        validate="one_to_one",
    )
    integrated = integrated.merge(
        rank_values,
        on=KEY_COLUMNS,
        how="left",
        validate="one_to_one",
    )

    expected_columns = (
        IDENTIFIER_COLUMNS
        + [f"cutoff_{column}" for column in CATEGORY_COLUMNS]
        + [f"cutoff_{column}" for column in PARTIAL_COLUMNS]
        + [f"rank_{column}" for column in CATEGORY_COLUMNS]
        + [f"rank_{column}" for column in PARTIAL_COLUMNS]
    )
    integrated = integrated[expected_columns]

    if len(integrated) != EXPECTED_ROWS:
        fail(f"output row count is {len(integrated)}, expected {EXPECTED_ROWS}")
    if duplicate_key_count(integrated):
        fail("integrated output contains duplicate join keys")
    if set(integrated.columns) != set(expected_columns):
        fail("integrated output columns do not match the expected schema")

    integrated.to_csv(OUTPUT_PATH, index=False)

    cutoff_hash_after = file_hash(CUTOFF_PATH)
    rank_hash_after = file_hash(RANK_PATH)
    sources_unchanged = (
        cutoff_hash_before == cutoff_hash_after
        and rank_hash_before == rank_hash_after
    )
    if not sources_unchanged:
        fail("a source file hash changed during integration")

    null_counts = integrated.isna().sum()
    year_distribution = integrated.groupby("year").size().to_dict()
    report_lines = [
        "TNEA STAGE 3 - VALIDATED CUTOFF + RANK INTEGRATION REPORT",
        "===========================================================",
        "",
        "STATUS: SUCCESS",
        "",
        "INPUT FILES",
        "-----------",
        f"Cutoff file: {CUTOFF_PATH}",
        f"Rank file: {RANK_PATH}",
        f"Cutoff input rows: {len(cutoff)}",
        f"Rank input rows: {len(rank)}",
        f"Cutoff input columns: {len(cutoff.columns)}",
        f"Rank input columns: {len(rank.columns)}",
        "",
        "JOIN VALIDATION",
        "---------------",
        f"Join key: {', '.join(KEY_COLUMNS)}",
        f"Cutoff duplicate key rows: {cutoff_duplicates}",
        f"Rank duplicate key rows: {rank_duplicates}",
        f"Unmatched cutoff keys: {len(unmatched_cutoff_keys)}",
        f"Unmatched rank keys: {len(unmatched_rank_keys)}",
        f"Identifier conflicts: {conflicts}",
        "Branch-name conflicts are documented but are non-fatal because branch_code is the join identifier.",
        "Join validation: PASS",
        "",
        "OUTPUT VALIDATION",
        "------------------",
        f"Output file: {OUTPUT_PATH}",
        f"Output row count: {len(integrated)}",
        f"Output column count: {len(integrated.columns)}",
        f"Output row count equals {EXPECTED_ROWS}: {len(integrated) == EXPECTED_ROWS}",
        f"Output keys unique: {duplicate_key_count(integrated) == 0}",
        "Missing values were preserved; no missing value was converted to zero.",
        "",
        "YEAR DISTRIBUTION",
        "-----------------",
    ]
    report_lines.extend(f"{year}: {count}" for year, count in sorted(year_distribution.items()))
    report_lines.extend(
        [
            "",
            "OUTPUT NULL COUNTS",
            "------------------",
        ]
    )
    report_lines.extend(f"{column}: {int(count)}" for column, count in null_counts.items())
    report_lines.extend(
        [
            "",
            "SOURCE INTEGRITY",
            "----------------",
            f"Cutoff source unchanged: {cutoff_hash_before == cutoff_hash_after}",
            f"Rank source unchanged: {rank_hash_before == rank_hash_after}",
            f"All source files unchanged: {sources_unchanged}",
            f"Cutoff SHA-256 before: {cutoff_hash_before}",
            f"Cutoff SHA-256 after:  {cutoff_hash_after}",
            f"Rank SHA-256 before:   {rank_hash_before}",
            f"Rank SHA-256 after:    {rank_hash_after}",
            "",
            "GENERATED FILES",
            "----------------",
            str(OUTPUT_PATH),
            str(REPORT_PATH),
            "",
            "No ML training, feature engineering, prediction, source deletion, or source modification was performed.",
        ]
    )
    REPORT_PATH.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print("STAGE 3 INTEGRATION SUCCESS")
    print(f"Input cutoff rows: {len(cutoff)}")
    print(f"Input rank rows: {len(rank)}")
    print(f"Output rows: {len(integrated)}")
    print(f"Output columns: {len(integrated.columns)}")
    print(f"Unmatched cutoff keys: {len(unmatched_cutoff_keys)}")
    print(f"Unmatched rank keys: {len(unmatched_rank_keys)}")
    print(f"Duplicate cutoff keys: {cutoff_duplicates}")
    print(f"Duplicate rank keys: {rank_duplicates}")
    print(f"Output keys unique: {duplicate_key_count(integrated) == 0}")
    print(f"Sources unchanged: {sources_unchanged}")
    print("Generated files:")
    print(f"- {OUTPUT_PATH}")
    print(f"- {REPORT_PATH}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(str(error))
        raise SystemExit(1) from error
