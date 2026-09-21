import requests
import hashlib
import base64
import json
import csv
import os
import time
from pathlib import Path

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


API_URL = "https://cutoff.tneaonline.org/api/cutoff"

TOKEN = "1392036e-1777-4d43-8758-8f1587b1798a"

YEARS = [2021, 2022, 2023, 2024, 2025]

PAGE_SIZE = 50

OUTPUT_DIR = str(Path(__file__).resolve().parents[2] / "data" / "raw" / "cutoff")


def decrypt_tnea_response(response_data, token):

    key_text = "tnea-portal-aes-2026-static" + token
    key = hashlib.sha256(key_text.encode()).digest()

    iv = base64.b64decode(response_data["iv"])
    encrypted_data = base64.b64decode(response_data["data"])

    cipher = AES.new(
        key,
        AES.MODE_CBC,
        iv
    )

    decrypted = cipher.decrypt(encrypted_data)

    decrypted = unpad(
        decrypted,
        AES.block_size
    )

    return json.loads(
        decrypted.decode("utf-8")
    )


def get_page(year, page):

    params = {
        "type": "cutoff",
        "year": year,
        "page": page,
        "pageSize": PAGE_SIZE
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
        headers=headers,
        timeout=30
    )

    if response.status_code == 401:

        raise Exception(
            "TNEA TOKEN EXPIRED OR INVALID.\n"
            "Get a fresh Bearer token from Chrome DevTools."
        )

    response.raise_for_status()

    encrypted_data = response.json()

    return decrypt_tnea_response(
        encrypted_data,
        TOKEN
    )


def collect_year(year):

    print()
    print("=" * 50)
    print(f"COLLECTING YEAR {year}")
    print("=" * 50)

    all_records = []

    page = 1

    while True:

        print(f"Fetching page {page}...")

        result = get_page(
            year,
            page
        )

        records = result["data"]

        all_records.extend(records)

        total = result["total"]

        print(
            f"Received {len(records)} records "
            f"| Collected {len(all_records)}/{total}"
        )

        if len(all_records) >= total:
            break

        page += 1

        # Small delay between requests
        time.sleep(0.3)

    return all_records


def save_csv(records, year):

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    filename = os.path.join(
        OUTPUT_DIR,
        f"tnea_{year}.csv"
    )

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

    print(f"Saved: {filename}")


def main():

    for year in YEARS:

        records = collect_year(year)

        print(
            f"\nYear {year} complete."
        )

        print(
            f"Total records: {len(records)}"
        )

        save_csv(
            records,
            year
        )


    print()
    print("=" * 50)
    print("ALL FIVE YEARS COMPLETE")
    print("=" * 50)


if __name__ == "__main__":
    main()
