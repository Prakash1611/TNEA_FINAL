import requests
import hashlib
import base64
import json

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


API_URL = "https://cutoff.tneaonline.org/api/meta"

TOKEN = "1392036e-1777-4d43-8758-8f1587b1798a"


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
    decrypted = unpad(decrypted, AES.block_size)

    return json.loads(decrypted.decode("utf-8"))


headers = {
    "accept": "application/json, text/plain, */*",
    "authorization": f"Bearer {TOKEN}",
    "referer": "https://cutoff.tneaonline.org/search",
    "user-agent": "Mozilla/5.0"
}


response = requests.get(
    API_URL,
    headers=headers
)

print("Status:", response.status_code)

if response.status_code == 401:
    print("TOKEN IS INVALID OR EXPIRED")
    exit()

response.raise_for_status()

encrypted_data = response.json()

print("Encrypted meta response received.")

meta = decrypt_tnea_response(
    encrypted_data,
    TOKEN
)

print("\n================ META DATA ================\n")

print(json.dumps(meta, indent=4))
