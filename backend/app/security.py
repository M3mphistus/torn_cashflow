import time

import jwt
from cryptography.fernet import Fernet

from .config import settings

JWT_ALGORITHM = "HS256"
JWT_EXPIRY_SECONDS = 400 * 86400  # ~400 days — matches browsers' own cookie lifetime cap.


def create_session_token(player_id: int) -> str:
    now = int(time.time())
    payload = {"playerId": player_id, "issuedAt": now, "exp": now + JWT_EXPIRY_SECONDS}
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_session_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


def _fernet() -> Fernet:
    return Fernet(settings.api_key_encryption_secret.encode())


def encrypt_api_key(raw_api_key: str) -> str:
    return _fernet().encrypt(raw_api_key.encode()).decode()


def decrypt_api_key(encrypted_api_key: str) -> str:
    return _fernet().decrypt(encrypted_api_key.encode()).decode()


def mask_key(api_key: str) -> str:
    if not api_key:
        return ""
    if len(api_key) <= 4:
        return "*" * len(api_key)
    return "*" * (len(api_key) - 4) + api_key[-4:]
