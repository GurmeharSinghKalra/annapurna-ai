"""Password hashing, opaque session tokens, and login throttling."""

import hashlib
import secrets
import time
from collections import defaultdict, deque
from threading import Lock

# OWASP's 2023 guidance for PBKDF2-HMAC-SHA256.
PBKDF2_ITERATIONS = 600_000
PBKDF2_ALGORITHM = "pbkdf2_sha256"
TOKEN_BYTES = 32


def hash_password(password: str, *, iterations: int = PBKDF2_ITERATIONS) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"{PBKDF2_ALGORITHM}${iterations}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Verify a password, transparently accepting the legacy `salt$digest` format."""
    parts = stored.split("$")
    if len(parts) == 4:
        algorithm, raw_iterations, salt, digest = parts
        if algorithm != PBKDF2_ALGORITHM:
            return False
        try:
            iterations = int(raw_iterations)
        except ValueError:
            return False
    elif len(parts) == 2:
        # Records written before the format carried its own parameters.
        salt, digest = parts
        iterations = 100_000
    else:
        return False

    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return secrets.compare_digest(candidate.hex(), digest)


def needs_rehash(stored: str) -> bool:
    parts = stored.split("$")
    if len(parts) != 4:
        return True
    try:
        return parts[0] != PBKDF2_ALGORITHM or int(parts[1]) < PBKDF2_ITERATIONS
    except ValueError:
        return True


def generate_session_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_session_token(token: str) -> str:
    """Tokens are stored hashed so a database leak does not hand out live sessions."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class RateLimiter:
    """Fixed-memory sliding window, keyed per caller.

    In-process only: it protects a single-instance deployment. Put a shared
    limiter in front of the API before running more than one worker.
    """

    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _prune(self, bucket: deque[float], now: float) -> None:
        cutoff = now - self.window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.popleft()

    def check(self, key: str) -> bool:
        """Return True when the caller is still under the limit."""
        now = time.monotonic()
        with self._lock:
            bucket = self._hits[key]
            self._prune(bucket, now)
            return len(bucket) < self.limit

    def record_failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            bucket = self._hits[key]
            self._prune(bucket, now)
            bucket.append(now)

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._hits.clear()
            else:
                self._hits.pop(key, None)

    def retry_after(self, key: str) -> int:
        now = time.monotonic()
        with self._lock:
            bucket = self._hits[key]
            self._prune(bucket, now)
            if not bucket:
                return 0
            return max(1, int(self.window_seconds - (now - bucket[0])))
