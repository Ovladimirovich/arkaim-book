import hashlib
import secrets


PREFIX_LEN = 8
RAW_LEN = 32


def generate_api_key() -> tuple[str, str, str]:
    raw = secrets.token_urlsafe(RAW_LEN)
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    prefix = raw[:PREFIX_LEN]
    return raw, key_hash, prefix


def mask_api_key(key: str) -> str:
    if not key:
        return ""
    return key[:PREFIX_LEN] + "..." + key[-4:]
