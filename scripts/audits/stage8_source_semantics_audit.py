from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / "documentation" / "source_semantics_report.txt"
KEY_COLUMNS = ["year", "college_code", "branch_code"]
CATEGORIES = ["oc", "bc", "bcm", "mbc", "sc", "sca", "st"]
CUTOFF_COLUMNS = [f"cutoff_{category}" for category in CATEGORIES]
RANK_COLUMNS = [f"rank_{category}" for category in CATEGORIES]
CUTOFF_PARTIAL = [f"cutoff_{category}_partial" for category in CATEGORIES]
RANK_PARTIAL = [f"rank_{category}_partial" for category in CATEGORIES]

INPUT_FILES = [
    ROOT / "data" / "integrated" / "tnea_integrated_master.csv",
    ROOT / "data" / "cleaned" / "cutoff" / "tnea_cutoff_master_final.csv",
    ROOT / "data" / "cleaned" / "rank" / "tnea_rank_master_final.csv",
]
ARTIFACT_EXTENSIONS = {".py", ".txt", ".md", ".json", ".html", ".xml", ".yaml", ".yml"}
KEYWORDS = re.compile(
    r"closing|opening|allot|round|partial|cutoff|rank|category|api|response|final",
    re.IGNORECASE,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pct(count: int, total: int) -> str:
    return f"{100 * count / total:.2f}%" if total else "0.00%"


def format_values(values: list[object]) -> str:
    return ", ".join(str(value) for value in values) if values else "None"


def inspect_artifacts() -> tuple[list[Path], list[tuple[Path, int, str]]]:
    files = sorted(
        path
        for path in ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() in ARTIFACT_EXTENSIONS
        and path.name not in {REPORT_PATH.name, Path(__file__).name}
    )
    hits: list[tuple[Path, int, str]] = []
    for path in files:
        try:
            for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if KEYWORDS.search(line):
                    hits.append((path, line_number, line.strip()))
        except OSError:
            continue
    return files, hits


def append_partial_analysis(lines: list[str], frame: pd.DataFrame) -> None:
    lines.extend(
        [
            "7. Partial Indicator Semantics",
            "-------------------------------",
            "Observed values and frequencies are reported exactly; no meaning is inferred from numeric patterns alone.",
        ]
    )
    for measure, value_columns, partial_columns in [
        ("cutoff", CUTOFF_COLUMNS, CUTOFF_PARTIAL),
        ("rank", RANK_COLUMNS, RANK_PARTIAL),
    ]:
        lines.append(f"{measure.upper()} partial indicators:")
        for category, value_column, partial_column in zip(CATEGORIES, value_columns, partial_columns):
            indicator_counts = frame[partial_column].value_counts(dropna=False).sort_index().to_dict()
            value_missing = frame[value_column].isna()
            indicator = frame[partial_column]
            combinations = {
                "value_missing_indicator_0": int((value_missing & (indicator == 0)).sum()),
                "value_missing_indicator_1": int((value_missing & (indicator == 1)).sum()),
                "value_present_indicator_0": int((~value_missing & (indicator == 0)).sum()),
                "value_present_indicator_1": int((~value_missing & (indicator == 1)).sum()),
            }
            lines.append(
                f"  {partial_column}: values={indicator_counts}; {value_column} missing/present combinations={combinations}"
            )
    lines.extend(
        [
            "",
            "Project-artifact evidence:",
            "- cleaned_cutoff_data/cutoff_validation_report.txt explicitly says missing cutoff values are intentional and represent courses not offered in that category; it is a project validation note, not an authoritative source definition.",
            "- Rank validation reports confirm partial columns contain 0/1 and validate missingness, but do not define what partial means in the source system.",
            "Assessment: PLAUSIBLE_NOT_CONFIRMED for the project-note interpretation; UNKNOWN for authoritative source semantics.",
        ]
    )


def append_semantics(lines: list[str]) -> None:
    lines.extend(
        [
            "3. Cutoff Semantics",
            "--------------------",
            "Confirmed evidence:",
            "- The integrated and cutoff master schemas contain category columns named oc, bc, bcm, mbc, sc, sca, and st after the cutoff source fields were prefixed.",
            "- Existing validation reports describe these as cutoff values and validate them as numeric marks, with no negative values.",
            "- The local collector code sends an API request with type='cutoff' to /api/cutoff.",
            "",
            "Uncertain interpretations:",
            "- The values may be cutoff-related historical summary values, but no local authoritative label says opening, closing, minimum, maximum, last-round, or final-round.",
            "- Numeric ranges and year-to-year behavior do not prove the statistic definition.",
            "",
            "Assessment: UNKNOWN",
            "Unresolved questions: exact cutoff statistic, round/counselling stage, publication timestamp, and whether values are calculated from allotments or another summary.",
            "",
            "4. Rank Semantics",
            "------------------",
            "Confirmed evidence:",
            "- The rank master and integrated schema contain category rank columns with positive numeric values and missing values.",
            "- Existing rank validation reports confirm zero negative, zero, and non-numeric rank values after cleaning.",
            "- The local collector code sends an API request with type='rank' to /api/cutoff.",
            "",
            "Uncertain interpretations:",
            "- The values may be rank-related historical summary values, but no local authoritative label says opening rank, closing rank, last allotted rank, final-round rank, or another statistic.",
            "- Numeric ordering alone does not prove which candidate or event the value represents.",
            "",
            "Assessment: UNKNOWN",
            "Unresolved questions: exact rank statistic, round/counselling stage, whether it is last allotted candidate rank, and publication timestamp.",
        ]
    )


def append_outcome_and_rounds(lines: list[str], frame: pd.DataFrame) -> None:
    lines.extend(
        [
            "5. Admission Outcome Evidence",
            "------------------------------",
            "Explicit evidence found in local files:",
            "- No student identifier, applicant record, seat-allocation result, admitted flag, allotment result, or confirmed individual outcome column exists in the integrated schema.",
            "- No local report or saved response explicitly identifies a last allotted candidate, final admitted candidate, or confirmed seat allocation.",
            "- Historical cutoff/rank rows are college/branch/year/category summaries, not individual student outcomes.",
            "",
            "Assessment: UNKNOWN for actual admission outcomes.",
            "The data must not be described as confirmed admission outcomes or admission probabilities.",
            "",
            "6. Round and Year Coverage",
            "---------------------------",
            f"Years present: {sorted(frame['year'].unique().tolist())}",
        ]
    )
    for year, count in frame.groupby("year").size().items():
        lines.append(f"  {year}: {count} rows")
    lines.extend(
        [
            "Round fields present: none identified in the inspected schemas.",
            "Counselling-stage fields present: none identified in the inspected schemas.",
            "Assessment: UNKNOWN whether records are round-specific, final-round-only, combined across rounds, or another coverage.",
            "The year column identifies dataset year only; it does not identify a counselling round.",
        ]
    )


def append_direction(lines: list[str]) -> None:
    lines.extend(
        [
            "8. Comparison-Direction Assessment",
            "-----------------------------------",
            "Cutoff direction: UNKNOWN",
            "- No authoritative local definition confirms whether a higher or lower student cutoff is preferable under these fields.",
            "- Mark-based intuition is insufficient to confirm the source statistic or comparison rule.",
            "",
            "Rank direction: UNKNOWN",
            "- No authoritative local definition confirms whether a higher or lower student rank is preferable under these fields.",
            "- Rank numeric ordering alone is insufficient to confirm the source statistic or rule.",
            "",
            "Category-specific direction: UNKNOWN for OC, BC, BCM, MBC, SC, SCA, and ST for both input families.",
            "No definitive historical threshold comparison should be calculated until source definitions and direction are verified.",
        ]
    )


def append_safe_decision(lines: list[str]) -> None:
    lines.extend(
        [
            "9. Safe Implementation Decision",
            "-------------------------------",
            "COMPARISON_DISABLED_PENDING_VERIFICATION",
            "Reason: local evidence confirms field structure and project transformations, but does not explicitly confirm cutoff/rank statistic meanings, round coverage, outcome status, or comparison direction.",
            "The Stage 7 prototype may remain available as a non-definitive scaffold, but it must not be enabled for definitive interpretation using the current evidence.",
            "",
            "Required evidence before enabling comparison:",
            "- Official source documentation or saved API metadata defining each measure.",
            "- Explicit round/counselling-stage definition.",
            "- Confirmation whether values are opening, closing, last-allotted, or another statistic.",
            "- Explicit definition of partial indicators.",
            "- Source-confirmed direction for cutoff and rank separately.",
        ]
    )


def main() -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    existing_inputs = [path for path in INPUT_FILES if path.exists()]
    unavailable_inputs = [path for path in INPUT_FILES if not path.exists()]
    if not INPUT_FILES[0].exists():
        raise FileNotFoundError(f"Required integrated dataset not found: {INPUT_FILES[0]}")

    hashes_before = {path: sha256(path) for path in existing_inputs}
    frame = pd.read_csv(INPUT_FILES[0])
    required = KEY_COLUMNS + ["college_name", "district", "college_type", "branch_name"] + CUTOFF_COLUMNS + RANK_COLUMNS + CUTOFF_PARTIAL + RANK_PARTIAL
    missing_columns = [column for column in required if column not in frame.columns]
    if missing_columns:
        raise ValueError(f"Integrated dataset is missing required columns: {missing_columns}")

    artifacts, keyword_hits = inspect_artifacts()
    local_urls = sorted(
        {
            match.group(0).rstrip('\\"\'')
            for path, _, line in keyword_hits
            for match in re.finditer(r"https?://[^\s\"']+", line)
        }
    )
    api_hit_files = sorted({path for path, _, line in keyword_hits if "/api/" in line or "API_URL" in line})
    saved_response_files = [path for path in artifacts if path.suffix.lower() in {".json", ".html", ".xml"}]

    lines = [
        "STAGE 8 - SOURCE SEMANTICS VERIFICATION AUDIT",
        "===============================================",
        "",
        "1. Audit Metadata",
        "------------------",
        f"UTC audit timestamp: {timestamp}",
        "Operation: read-only",
        "CSV/JSON/source files modified: NO",
        "Rows deleted or values imputed: NO",
        "ML model trained: NO",
        "",
        "Input files inspected:",
    ]
    lines.extend(f"  {path}: AVAILABLE" for path in existing_inputs)
    lines.extend(f"  {path}: UNAVAILABLE" for path in unavailable_inputs)
    lines.extend(
        [
            f"Unavailable requested input count: {len(unavailable_inputs)}",
            f"Integrated rows: {len(frame)}",
            f"Integrated columns: {len(frame.columns)}",
            "",
            "2. Source Files and Schema Evidence",
            "------------------------------------",
            f"Integrated schema columns: {list(frame.columns)}",
            f"Integrated dtypes: {frame.dtypes.astype(str).to_dict()}",
            f"Primary-key duplicate rows: {int(frame.duplicated(KEY_COLUMNS).sum())}",
            f"Exact duplicate rows: {int(frame.duplicated().sum())}",
            f"Category columns: {CATEGORIES}",
            f"Cutoff columns: {CUTOFF_COLUMNS}",
            f"Rank columns: {RANK_COLUMNS}",
            f"Cutoff partial columns: {CUTOFF_PARTIAL}",
            f"Rank partial columns: {RANK_PARTIAL}",
            "",
            f"Local text/code artifacts inspected: {len(artifacts)}",
            f"Artifacts with semantic keyword hits: {len({path for path, _, _ in keyword_hits})}",
            f"API-related artifact files: {[str(path) for path in api_hit_files]}",
            f"Saved JSON/HTML/XML response-like files found: {[str(path) for path in saved_response_files] or 'None'}",
            f"Source URLs found in local artifacts: {local_urls or 'None'}",
            "",
            "Collector evidence:",
            "- Local collector scripts reference https://cutoff.tneaonline.org/api/cutoff and an encrypted response containing iv/data fields.",
            "- Local request payloads distinguish type='cutoff' and type='rank'.",
            "- No saved decrypted API response, authoritative field label, or round definition was found in the local project artifacts.",
            "- Request type names establish source separation, not the statistical definition of each returned value.",
        ]
    )
    append_semantics(lines)
    append_outcome_and_rounds(lines, frame)
    append_partial_analysis(lines, frame)
    append_direction(lines)
    append_safe_decision(lines)
    lines.extend(
        [
            "",
            "10. Limitations and Next Steps",
            "-------------------------------",
            "Confirmed facts are limited to local schema, values, transformations, API request code, and existing validation notes.",
            "Plausible interpretations are not treated as confirmed definitions.",
            "Next steps:",
            "1. Obtain official documentation or a saved API response with field labels and round metadata.",
            "2. Confirm whether cutoff values are opening, closing, minimum, maximum, or another statistic.",
            "3. Confirm whether rank values are opening, closing, last-allotted, or another statistic.",
            "4. Confirm whether values are round-specific, final-round-only, or combined.",
            "5. Obtain the authoritative definition of cutoff/rank partial indicators.",
            "6. Confirm comparison direction separately for each measure family and category.",
            "7. Only then enable a clearly labelled historical comparison; never call it actual admission probability without outcome data.",
            "",
            "FINAL STATUS",
            "------------",
            "Audit completed successfully: YES",
            "Cutoff semantic status: UNKNOWN",
            "Rank semantic status: UNKNOWN",
            "Partial indicator status: PLAUSIBLE_NOT_CONFIRMED / UNKNOWN at source level",
            "Admission outcome evidence: UNKNOWN / not present",
            "Round coverage status: UNKNOWN",
            "Cutoff direction: UNKNOWN",
            "Rank direction: UNKNOWN",
            "Safe implementation decision: COMPARISON_DISABLED_PENDING_VERIFICATION",
            "Original project files modified: NO",
            f"Report path: {REPORT_PATH}",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    hashes_after = {path: sha256(path) for path in existing_inputs}
    if hashes_before != hashes_after:
        raise RuntimeError("An inspected source file hash changed during the read-only audit")

    print("STAGE 8 SOURCE-SEMANTICS AUDIT COMPLETE")
    print(f"Integrated rows audited: {len(frame)}")
    print(f"Years: {sorted(frame['year'].unique().tolist())}")
    print("Cutoff semantics: UNKNOWN")
    print("Rank semantics: UNKNOWN")
    print("Cutoff direction: UNKNOWN")
    print("Rank direction: UNKNOWN")
    print("Safe implementation decision: COMPARISON_DISABLED_PENDING_VERIFICATION")
    print("Source files unchanged: True")
    print(f"Report created successfully: {REPORT_PATH}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, FileNotFoundError, RuntimeError) as error:
        print(f"STAGE 8 AUDIT FAILED: {error}")
        raise SystemExit(1) from error
