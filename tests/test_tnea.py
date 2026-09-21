import requests
import hashlib
import base64
import json

URL = "https://cutoff.tneaonline.org/api/cutoff"

TOKEN = "1392036e-1777-4d43-8758-8f1587b1798a"

params = {
    "type": "cutoff",
    "year": 2025,
    "page": 1,
    "pageSize": 50,
    "district": "COIMBATORE",
    "branch": "CS"
}

headers = {
    "accept": "application/json, text/plain, */*",
    "authorization": f"Bearer {TOKEN}",
    "referer": "https://cutoff.tneaonline.org/search",
    "user-agent": "Mozilla/5.0"
}


def decrypt_tnea_response(response_data, token):

    # Same key generation used by TNEA website
    key_text = "tnea-portal-aes-2026-static" + token
    key = hashlib.sha256(key_text.encode()).digest()

    # Decode IV and encrypted data
    iv = base64.b64decode(response_data["iv"])
    encrypted_data = base64.b64decode(response_data["data"])

    # AES-CBC decryption
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad

    cipher = AES.new(
        key,
        AES.MODE_CBC,
        iv
    )

    decrypted = cipher.decrypt(encrypted_data)

    # Remove PKCS7 padding
    decrypted = unpad(decrypted, AES.block_size)

    # Convert to JSON
    decrypted_text = decrypted.decode("utf-8")

    return json.loads(decrypted_text)


response = requests.get(
    URL,
    params=params,
    headers=headers
)

print("Status:", response.status_code)
print("URL:", response.url)

if response.status_code == 200:

    encrypted_response = response.json()

    print("\nEncrypted response received.")

    try:
        data = decrypt_tnea_response(
            encrypted_response,
            TOKEN
        )

        print("\n========== DECRYPTED DATA ==========\n")

        print(json.dumps(data, indent=4))

    except Exception as e:
        print("\nDecryption failed:")
        print(type(e).__name__, e)

else:
    print("\nRequest failed:")
    print(response.text)
