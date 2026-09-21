import requests
import hashlib
import base64
import json
import csv
import os
from pathlib import Path

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


API_URL = "https://cutoff.tneaonline.org/api/cutoff"

# Put your CURRENT working token here
TOKEN = "72f474c1-f0c7-4304-8b9b-03ad571f240f"


def decrypt_tnea_response(response_data, token):

    key_text = "tnea-portal-aes-2026-static" + token
    key = hashlib.sha256(key_text.encode()).digest()

    iv = base64.b64decode(response_data["iv"])
    encrypted_data = base64.b64decode(response_data["data"])

    cipher = AES.new(key, AES.MODE_CBC, iv)

    decrypted = cipher.decrypt(encrypted_data)
    decrypted = unpad(decrypted, AES.block_size)

    return json.loads(decrypted.decode("utf-8"))


def get_page(year, page):

    params = {
        "type": "rank",
        "year": year,
        "page": page,
        "pageSize": 50
    }

    headers = {
        "accept": "application/json, text/plain, */*",
        "authorization": f"Bearer {TOKEN}",
        "referer": "https://cutoff.tneaonline.org/search",
        "user-agent": "Mozilla/5.0"
    }

    response = requests.get(
        API_URL,
        params=params,
        headers=headers
    )

    if response.status_code == 401:
        raise Exception(
            "TNEA token expired or is invalid. "
            "Get a fresh Bearer token from Chrome DevTools."
        )

    response.raise_for_status()

    encrypted_data = response.json()

    return decrypt_tnea_response(
        encrypted_data,
        TOKEN
    )


def collect_all_pages(year):

    all_records = []

    page = 1

    while True:

        print(f"[{year}] Fetching page {page}...")

        result = get_page(
            year,
            page
        )

        records = result["data"]

        all_records.extend(records)

        total = result["total"]

        print(
            f"[{year}] Received {len(records)} records "
            f"| Total collected: {len(all_records)}/{total}"
        )

        if len(all_records) >= total:
            break

        page += 1

    return all_records


def save_csv(records, year):

    filename = Path(__file__).resolve().parents[2] / "data" / "raw" / "rank" / f"tnea_{year}_rank.csv"

    if not records:
        print(f"No records found for {year}")
        return

    with open(
        filename,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=records[0].keys()
        )

        writer.writeheader()
        writer.writerows(records)

    print(f"[{year}] Saved: {filename}")
    print()


# ==========================================
# COLLECT ALL 5 YEARS
# ==========================================

years = [2021, 2022, 2023, 2024, 2025]

for year in years:

    print()
    print("========================================")
    print(f"STARTING YEAR: {year}")
    print("========================================")

    records = collect_all_pages(year)

    print()
    print(f"{year} COMPLETE")
    print(f"Total records: {len(records)}")

    save_csv(records, year)


print()
print("========================================")
print("ALL RANK DATA COLLECTION COMPLETE")
print("========================================")
