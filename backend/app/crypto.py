import os
import base64
from cryptography.fernet import Fernet

def _get_fernet() -> Fernet:
    key = os.getenv("ENCRYPTION_KEY", "dev-encryption-key-32-bytes!!")
    # Fernet requires a 32-byte URL-safe base64 key
    key_bytes = key.encode()[:32].ljust(32, b"=")
    b64_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(b64_key)

def encrypt(value: str) -> str:
    if not value:
        return value
    f = _get_fernet()
    return f.encrypt(value.encode()).decode()

def decrypt(value: str) -> str:
    if not value:
        return value
    try:
        f = _get_fernet()
        return f.decrypt(value.encode()).decode()
    except Exception:
        # Return as-is if decryption fails (e.g. unencrypted legacy values)
        return value
