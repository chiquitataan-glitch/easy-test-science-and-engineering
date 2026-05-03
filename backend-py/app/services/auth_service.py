from datetime import datetime, timedelta, timezone

from passlib.context import CryptContext
from jose import jwt

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


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
