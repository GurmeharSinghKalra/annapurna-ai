"""Password hashing, access tokens, and refresh-token handling."""

from __future__ import annotations

import hashlib
import logging
import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from .config import settings

logger = logging.getLogger(__name__)

_hasher = PasswordHasher()

ACCESS_TOKEN_TYPE = "access"

# Indian mobile numbers: ten digits starting 6-9, optionally prefixed with +91 / 0.
_PHONE_PATTERN = re.compile(r"^(?:\+?91[\s-]?|0)?([6-9]\d{9})$")


class InvalidToken(Exception):
    """Raised when an access token is absent, malformed, expired, or not ours."""


def normalise_phone(raw: str) -> str:
    """Return the bare ten-digit mobile number, or raise ValueError.

    Normalising at the boundary is what makes `phone` safe as a unique login key: without it
    `9876543210`, `+919876543210` and `09876543210` would register as three separate accounts.
    """
    candidate = (raw or "").strip().replace(" ", "").replace("-", "")
    match = _PHONE_PATTERN.match(candidate)
    if not match:
        raise ValueError("Enter a valid 10-digit Indian mobile number")
    return match.group(1)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, stored_hash: str) -> tuple[bool, str | None]:
    """Return (is_valid, replacement_hash). The replacement is set when parameters have moved on."""
    try:
        _hasher.verify(stored_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False, None
    if _hasher.check_needs_rehash(stored_hash):
        return True, _hasher.hash(password)
    return True, None


def create_access_token(farmer_id: uuid.UUID) -> tuple[str, int]:
    """Return (jwt, expires_in_seconds)."""
    expires_in = settings.access_token_ttl_minutes * 60
    now = datetime.now(UTC)
    payload = {
        "sub": str(farmer_id),
        "typ": ACCESS_TOKEN_TYPE,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
        "iss": settings.jwt_issuer,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256"), expires_in


def decode_access_token(token: str) -> uuid.UUID:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise InvalidToken(str(exc)) from exc
    if payload.get("typ") != ACCESS_TOKEN_TYPE:
        raise InvalidToken("token is not an access token")
    try:
        return uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise InvalidToken("token subject is not a farmer id") from exc


def new_refresh_token() -> tuple[str, str, datetime]:
    """Return (raw_token, sha256_hash, expires_at). Only the hash is ever stored."""
    raw = secrets.token_urlsafe(48)
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_ttl_days)
    return raw, hash_refresh_token(raw), expires_at


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def password_problem(password: str) -> str | None:
    """Return a human-readable reason the password is unacceptable, or None."""
    if len(password) < 8:
        return "Password must be at least 8 characters"
    if len(password) > 200:
        return "Password must be 200 characters or fewer"
    if password.isdigit():
        return "Password must not be only digits"
    return None
