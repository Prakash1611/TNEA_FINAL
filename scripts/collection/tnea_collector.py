import requests
import hashlib
import base64
import json
import csv
from pathlib import Path

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


API_URL = "https://cutoff.tneaonline.org/api/cutoff"

TOKEN = "1392036e-1777-4d43-8758-8f1587b1798a"


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
        "type": "cutoff",
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

        print(f"Fetching page {page}...")

        result = get_page(
            year,
            page
        )

        records = result["data"]

        all_records.extend(records)

        total = result["total"]
        page_size = result["pageSize"]

        print(
            f"Received {len(records)} records "
            f"| Total collected: {len(all_records)}/{total}"
        )

        if len(all_records) >= total:
            break

        page += 1

    return all_records


records = collect_all_pages(
    year=2025
)


print()
print("================================")
print("COLLECTION COMPLETE")
print("================================")
print("Total records:", len(records))


output_path = Path(__file__).resolve().parents[2] / "exports" / "tnea_2025_coimbatore_cs.csv"

with open(
    output_path,
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


print(f"Saved: {output_path}")
