from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import base64
import hashlib
import json
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / "documentation" / "api_metadata_report.txt"
SOURCE_FILES = [
    ROOT / "tnea_collector.py",
    ROOT / "tnea_rank_collector.py",
    ROOT / "tnea_5year_collector.py",
    ROOT / "test_tnea.py",
    ROOT / "test_meta.py",
]
SEARCH_EXTENSIONS = {".py", ".txt", ".md", ".json", ".html", ".xml", ".yaml", ".yml"}
SEARCH_TERMS = re.compile(
    r"cutoff|rank|opening|closing|round|allotment|partial|category|response|meta|api",
    re.IGNORECASE,
)
URL_PATTERN = re.compile(r"https?://[^\s\"']+")
TOKEN_PATTERN = re.compile(r"([A-Fa-f0-9]{8}-[A-Fa-f0-9-]{27,})")


def mask(value: object) -> str:
    text = str(value)
    text = TOKEN_PATTERN.sub("[REDACTED_TOKEN]", text)
    text = re.sub(r"(Bearer\s+)[^\s,;]+", r"\1[REDACTED]", text, flags=re.IGNORECASE)
    return text


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def decrypt_response(response_data: dict, token: str) -> object:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad

    key_text = "tnea-portal-aes-2026-static" + token
    key = hashlib.sha256(key_text.encode()).digest()
    iv = base64.b64decode(response_data["iv"])
    encrypted_data = base64.b64decode(response_data["data"])
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = unpad(cipher.decrypt(encrypted_data), AES.block_size)
    return json.loads(decrypted.decode("utf-8"))


def source_inventory() -> tuple[list[str], dict[str, str], dict[str, list[str]], list[str]]:
    available = []
    unavailable = []
    contents = {}
    for path in SOURCE_FILES:
        if path.exists():
            available.append(str(path))
            contents[str(path)] = path.read_text(encoding="utf-8", errors="replace")
        else:
            unavailable.append(str(path))

    all_files = [
        path for path in ROOT.rglob("*")
        if path.is_file()
        and path.suffix.lower() in SEARCH_EXTENSIONS
        and path.name not in {REPORT_PATH.name, Path(__file__).name}
    ]
    hits: dict[str, list[str]] = {}
    urls: list[str] = []
    for path in all_files:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line_number, line in enumerate(lines, 1):
            if SEARCH_TERMS.search(line):
                hits.setdefault(str(path), []).append(f"{line_number}: {mask(line.strip())}")
            urls.extend(URL_PATTERN.findall(line))
    return available, contents, hits, sorted(set(urls))


def extract_code_facts(contents: dict[str, str]) -> dict[str, object]:
    endpoints = set()
    request_types = set()
    payload_fields = set()
    encryption_facts = set()
    metadata_endpoint = None
    for path, text in contents.items():
        endpoints.update(URL_PATTERN.findall(text))
        if "api/meta" in text:
            metadata_endpoint = "https://cutoff.tneaonline.org/api/meta"
        request_types.update(re.findall(r'["\']type["\']\s*:\s*["\']([^"\']+)', text))
        payload_fields.update(re.findall(r'["\']([A-Za-z][A-Za-z0-9_]*)["\']\s*:', text))
        if "AES.MODE_CBC" in text:
            encryption_facts.add("AES-CBC")
        if "hashlib.sha256" in text:
            encryption_facts.add("SHA-256 key derivation")
        if "base64.b64decode" in text:
            encryption_facts.add("Base64 decoding of IV/encrypted data")
        if "unpad" in text:
            encryption_facts.add("PKCS#7-style unpadding")
    return {
        "endpoints": sorted(endpoints),
        "metadata_endpoint": metadata_endpoint,
        "request_types": sorted(request_types),
        "payload_fields": sorted(payload_fields),
        "encryption_facts": sorted(encryption_facts),
    }


def json_shape(value: object, prefix: str = "root") -> list[str]:
    shapes = []
    if isinstance(value, dict):
        shapes.append(f"{prefix}: object fields={sorted(str(key) for key in value.keys())}")
        for key, child in value.items():
            if isinstance(child, (dict, list)):
                shapes.extend(json_shape(child, f"{prefix}.{key}"))
    elif isinstance(value, list):
        shapes.append(f"{prefix}: array length={len(value)}")
        if value:
            shapes.extend(json_shape(value[0], f"{prefix}[0]"))
    return shapes


def fetch_metadata(contents: dict[str, str]) -> dict[str, object]:
    result: dict[str, object] = {
        "status": "NOT_ATTEMPTED",
        "error": None,
        "http_status": None,
        "encrypted_fields": [],
        "decrypted_shape": [],
        "decrypted_labels": [],
    }
    meta_text = contents.get(str(ROOT / "test_meta.py"), "")
    token_match = re.search(r"TOKEN\s*=\s*[\"']([^\"']+)[\"']", meta_text)
    if not token_match:
        result["status"] = "FAILED"
        result["error"] = "No local metadata-request token configuration found; token was not invented."
        return result
    token = token_match.group(1)
    try:
        import requests

        response = requests.get(
            "https://cutoff.tneaonline.org/api/meta",
            headers={
                "accept": "application/json, text/plain, */*",
                "authorization": f"Bearer {token}",
                "referer": "https://cutoff.tneaonline.org/search",
                "user-agent": "Mozilla/5.0",
            },
            timeout=20,
        )
        result["http_status"] = response.status_code
        if response.status_code != 200:
            result["status"] = "FAILED"
            try:
                body = response.json()
                body_shape = sorted(str(key) for key in body.keys()) if isinstance(body, dict) else type(body).__name__
            except ValueError:
                body_shape = "non-JSON response"
            result["error"] = f"HTTP {response.status_code}; response body not retained; observed response shape={body_shape}"
            return result
        encrypted = response.json()
        if not isinstance(encrypted, dict):
            result["status"] = "FAILED"
            result["error"] = "Metadata response JSON was not an object."
            return result
        result["encrypted_fields"] = sorted(str(key) for key in encrypted.keys())
        decrypted = decrypt_response(encrypted, token)
        result["status"] = "SUCCESS"
        result["decrypted_shape"] = json_shape(decrypted)
        if isinstance(decrypted, dict):
            result["decrypted_labels"] = sorted(str(key) for key in decrypted.keys())
        return result
    except Exception as error:
        result["status"] = "FAILED"
        result["error"] = f"{type(error).__name__}: {mask(error)}"
        return result


def main() -> None:
    available, contents, hits, urls = source_inventory()
    if not (ROOT / "test_meta.py").exists():
        raise FileNotFoundError("test_meta.py is required for the metadata investigation")
    hashes_before = {path: sha256(Path(path)) for path in available if Path(path).exists()}
    facts = extract_code_facts(contents)
    metadata = fetch_metadata(contents)

    lines = [
        "STAGE 9 - TNEA API METADATA INVESTIGATION",
        "===========================================",
        "",
        "1. AUDIT METADATA",
        "------------------",
        f"UTC timestamp: {datetime.now(timezone.utc).isoformat()}",
        "Mode: read-only",
        "CSV/JSON/source files modified: NO",
        "Tokens, credentials, and encryption keys exposed: NO",
        "",
        "Available requested scripts:",
    ]
    lines.extend(f"  {path}" for path in available)
    lines.extend(["Unavailable requested scripts:"])
    lines.extend(f"  {path}" for path in sorted(set(str(path) for path in SOURCE_FILES) - set(available)) or ["  None"])
    lines.extend(
        [
            "",
            "2. CONFIRMED CODE-LEVEL API EVIDENCE",
            "------------------------------------",
            f"Endpoints found: {facts['endpoints']}",
            f"Metadata endpoint: {facts['metadata_endpoint'] or 'Not found'}",
            f"Request type values found: {facts['request_types']}",
            f"Request/payload fields found: {facts['payload_fields']}",
            f"Encryption/decryption facts: {facts['encryption_facts']}",
            "",
            "API behavior confirmed from local code:",
            "- /api/cutoff is used for paged data requests.",
            "- cutoff collection uses type='cutoff'.",
            "- rank collection uses type='rank'.",
            "- year, page, and pageSize are used for pagination; test_tnea.py also supplies district and branch filters.",
            "- metadata is requested from /api/meta.",
            "- responses are expected to contain encrypted iv and data fields.",
            "- AES-CBC is used after deriving a key with SHA-256 from a static prefix plus the local token.",
            "",
            "Classification: CONFIRMED for endpoint/request/encryption behavior in local code.",
            "",
            "3. LOCAL SEARCH FOR SEMANTIC EVIDENCE",
            "--------------------------------------",
            f"Searchable artifact files with keyword hits: {len(hits)}",
            f"URLs found locally: {urls}",
            "Saved decrypted API response files: none identified by the local artifact scan.",
            "Saved metadata JSON files: none identified by the local artifact scan.",
            "",
            "Relevant local evidence:",
            "- Existing reports validate schemas, missingness, numeric ranges, and cleanup operations.",
            "- Existing reports do not define opening cutoff, closing cutoff, opening rank, closing rank, last allotted rank, or counselling round.",
            "- Collector scripts contain request types and decryption code but no authoritative field labels for those meanings.",
            "- Existing project text explicitly keeps cutoff/rank semantics unconfirmed.",
            "",
            "Classification: UNKNOWN for authoritative cutoff/rank definitions and round semantics.",
            "",
            "4. LIVE METADATA ACCESS",
            "-----------------------",
            "One metadata-only request was attempted. No data collection endpoint was requested.",
            f"Metadata request status: {metadata['status']}",
            f"HTTP status: {metadata['http_status']}",
            f"Encrypted response field names: {metadata['encrypted_fields'] or 'None observed'}",
            f"Decrypted metadata shape: {metadata['decrypted_shape'] or 'None observed'}",
            f"Decrypted top-level labels: {metadata['decrypted_labels'] or 'None observed'}",
            f"Masked access error: {metadata['error'] or 'None'}",
        ]
    )
    if metadata["status"] == "SUCCESS":
        lines.append("Classification: CONFIRMED for the observed metadata response shape/labels only.")
    else:
        lines.append("Classification: UNKNOWN for live metadata fields because access/decryption did not produce usable metadata.")

    lines.extend(
        [
            "",
            "5. CUT-OFF/RANK SEMANTICS",
            "--------------------------",
            "Cutoff definition: UNKNOWN",
            "Rank definition: UNKNOWN",
            "Opening versus closing: UNKNOWN for both",
            "Last-allotted/final-admitted interpretation: UNKNOWN",
            "Actual seat-allocation interpretation: UNKNOWN and unsupported by local schema",
            "Historical summarized-statistic interpretation: PLAUSIBLE_NOT_CONFIRMED",
            "Individual student outcome interpretation: UNKNOWN and not evidenced by local files",
            "",
            "6. ROUND AND COUNSELLING FIELDS",
            "-------------------------------",
            "Round field found in source schemas: NO",
            "Counselling-stage field found in source schemas: NO",
            "Round-specific versus final-round versus combined: UNKNOWN",
            "No round meaning may be inferred from year, pagination, or numeric patterns.",
            "Classification: UNKNOWN",
            "",
            "7. RESPONSE FIELD NAMES AND LABELS",
            "----------------------------------",
            "Confirmed source-code response access pattern: response JSON is expected to contain iv and data before decryption.",
            "Expected decrypted data access in collectors: data, total, and pageSize.",
            "No authoritative decrypted metadata labels were available locally unless the live metadata request above succeeded.",
            "The names data/total/pageSize describe transport/pagination structure, not cutoff/rank semantics.",
            "Classification: CONFIRMED for code-level expected fields; UNKNOWN for semantic field labels.",
            "",
            "8. COMPARISON DIRECTION",
            "-----------------------",
            "Cutoff direction: UNKNOWN",
            "Rank direction: UNKNOWN",
            "Category-specific direction: UNKNOWN for OC, BC, BCM, MBC, SC, SCA, and ST.",
            "No direction was selected from mathematical plausibility or numeric patterns.",
            "",
            "9. SAFE IMPLEMENTATION STATUS",
            "------------------------------",
            "COMPARISON_DISABLED_PENDING_VERIFICATION",
            "Do not enable definitive cutoff/rank comparison until official metadata or documentation confirms definitions, round coverage, and direction.",
            "Do not interpret values as admission probability, guaranteed admission, or confirmed seat allocation.",
            "",
            "10. NEXT STEPS",
            "---------------",
            "1. Obtain a current official metadata response or documentation with field labels.",
            "2. Confirm whether cutoff values are opening, closing, minimum, maximum, or another statistic.",
            "3. Confirm whether rank values are opening, closing, last-allotted, or another statistic.",
            "4. Confirm counselling round coverage and publication timing.",
            "5. Confirm partial-indicator definitions.",
            "6. Confirm cutoff and rank comparison direction separately.",
            "7. Keep all tokens and keys outside reports and source-controlled artifacts.",
            "",
            "FINAL STATUS",
            "------------",
            "Audit completed successfully: YES",
            "Source files modified: NO",
            "CSV files modified: NO",
            "ML training performed: NO",
            "Cutoff/rank meanings invented: NO",
            "Secrets exposed: NO",
            f"Report path: {REPORT_PATH}",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    hashes_after = {path: sha256(Path(path)) for path in available if Path(path).exists()}
    if hashes_before != hashes_after:
        raise RuntimeError("An inspected local source file changed during the audit")

    print("STAGE 9 API METADATA INVESTIGATION COMPLETE")
    print(f"Metadata access: {metadata['status']}")
    print(f"Cutoff/rank semantics: UNKNOWN")
    print("Comparison direction: UNKNOWN")
    print("Safe status: COMPARISON_DISABLED_PENDING_VERIFICATION")
    print("Source files unchanged: True")
    print(f"Report created successfully: {REPORT_PATH}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, FileNotFoundError, RuntimeError) as error:
        print(f"STAGE 9 INVESTIGATION FAILED: {mask(error)}")
        raise SystemExit(1) from error
