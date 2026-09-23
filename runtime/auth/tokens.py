from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from pydantic import BaseModel

from core.config import settings


class TokenPayload(BaseModel):
    sub: str
    role: str
    provider: str
    exp: datetime | None = None


def create_access_token(subject: str, role: str, provider: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(tz=timezone.utc) + (expires_delta or timedelta(hours=12))
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "provider": provider,
        "exp": expire,
    }
    token = jwt.encode(payload, settings.SESSION_SECRET, algorithm="HS256")
    return token


def decode_access_token(token: str) -> TokenPayload | None:
    try:
        payload = jwt.decode(token, settings.SESSION_SECRET, algorithms=["HS256"])
        return TokenPayload(**payload)
    except JWTError:
        return None


def mask_token(token: str) -> str:
    if not token:
        return ""
    visible = 8
    if len(token) <= visible:
        return token
    return token[:visible] + "..." + token[-4:]
