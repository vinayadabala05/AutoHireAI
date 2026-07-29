"""Security primitives: password hashing and JWT access tokens.

No auth endpoints exist yet — these are the low-level building blocks
(hash/verify, encode/decode) that the future auth flow will be built on top
of, so the primitives can be unit-tested independently of any route.
"""

from datetime import UTC, datetime, timedelta
from typing import Any, cast

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.settings import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def hash_password(plain_password: str) -> str:
    return cast(str, _pwd_context.hash(plain_password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return cast(bool, _pwd_context.verify(plain_password, hashed_password))


def create_access_token(
    subject: str, expires_delta: timedelta | None = None, extra_claims: dict[str, Any] | None = None
) -> str:
    """Create a signed JWT for `subject` (typically a user ID)."""
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: dict[str, Any] = {"sub": subject, "exp": expire}
    if extra_claims:
        payload.update(extra_claims)
    return cast(str, jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM))


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and verify a JWT. Returns None if invalid or expired."""
    try:
        return cast(dict[str, Any], jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM]))
    except JWTError:
        return None
