"""Shared FastAPI dependencies: database session, current farmer, and rate limiting."""

from __future__ import annotations

import time
from collections import deque
from threading import Lock
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_session
from .models import Farmer
from .security import InvalidToken, decode_access_token

SessionDep = Annotated[AsyncSession, Depends(get_session)]

# auto_error=False so the same dependency can serve both required and optional authentication.
_bearer = HTTPBearer(auto_error=False, description="Access token from POST /auth/login")
BearerDep = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]

_UNAUTHORISED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Sign in to use this endpoint",
    headers={"WWW-Authenticate": "Bearer"},
)


async def optional_farmer(session: SessionDep, credentials: BearerDep) -> Farmer | None:
    """Resolve the signed-in farmer, or None. Guest use of the product stays fully supported."""
    if credentials is None or not credentials.credentials:
        return None
    try:
        farmer_id = decode_access_token(credentials.credentials)
    except InvalidToken:
        return None
    farmer = await session.get(Farmer, farmer_id)
    if farmer is None or not farmer.is_active:
        return None
    return farmer


async def current_farmer(farmer: Annotated[Farmer | None, Depends(optional_farmer)]) -> Farmer:
    if farmer is None:
        raise _UNAUTHORISED
    return farmer


OptionalFarmerDep = Annotated[Farmer | None, Depends(optional_farmer)]
CurrentFarmerDep = Annotated[Farmer, Depends(current_farmer)]


class SlidingWindowLimiter:
    """In-process sliding-window limiter.

    Enough for one API container and for stopping a single client from draining the Gemini or
    mandi-feed quota. A multi-replica deployment should move this to Redis; `/health` reports
    which backend is in use so the gap is visible rather than assumed.
    """

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._lock = Lock()

    def check(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        """Return (allowed, retry_after_seconds)."""
        if limit <= 0:
            return True, 0
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            bucket = self._hits.setdefault(key, deque())
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                return False, max(1, int(bucket[0] + window_seconds - now) + 1)
            bucket.append(now)
            if len(self._hits) > 10_000:  # Bound memory against a spray of distinct client keys.
                for stale_key in [k for k, v in self._hits.items() if not v or v[-1] <= cutoff]:
                    self._hits.pop(stale_key, None)
            return True, 0


limiter = SlidingWindowLimiter()


def client_key(request: Request, farmer: Farmer | None = None) -> str:
    """Identify the caller for rate limiting: the account when known, else the peer address.

    X-Forwarded-For is deliberately ignored: it is client-supplied and trivially spoofed unless a
    trusted proxy count is configured, which would make the limiter useless.
    """
    if farmer is not None:
        return f"farmer:{farmer.id}"
    return f"ip:{request.client.host if request.client else 'unknown'}"


def rate_limit(name: str, limit: int, window_seconds: int):
    """Build a dependency that rate-limits a route by account or peer address."""

    async def dependency(request: Request, farmer: OptionalFarmerDep) -> None:
        allowed, retry_after = limiter.check(f"{name}:{client_key(request, farmer)}", limit, window_seconds)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please wait a moment and try again.",
                headers={"Retry-After": str(retry_after)},
            )

    return dependency
