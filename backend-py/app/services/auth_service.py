from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

from app.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def _parse_expires_in(expires_in: str) -> timedelta:
    value = int(expires_in[:-1])
    unit = expires_in[-1].lower()
    if unit == "h":
        return timedelta(hours=value)
    elif unit == "m":
        return timedelta(minutes=value)
    elif unit == "d":
        return timedelta(days=value)
    else:
        return timedelta(hours=24)


def create_token(user_id: str, role: str, membership_type: str) -> str:
    now = datetime.now(timezone.utc)
    expires_delta = _parse_expires_in(settings.JWT_EXPIRES_IN)
    payload = {
        "sub": user_id,
        "role": role,
        "membership_type": membership_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
