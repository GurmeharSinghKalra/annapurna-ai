import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Iterator

from .config import get_settings
from .schemas import HistoryRecord, UserCreate
from .security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    needs_rehash,
    verify_password,
)


def _db_path():
    settings = get_settings()
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    return settings.database_path


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Transactional connection that is always closed.

    `with sqlite3.connect(...)` only commits or rolls back the transaction; it
    leaves the connection (and its file descriptor) open. This wrapper does both.
    """
    connection = sqlite3.connect(_db_path())
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}


def init_database() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                language TEXT NOT NULL,
                location TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS recommendation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                farmer_name TEXT NOT NULL,
                location TEXT NOT NULL,
                crop TEXT NOT NULL,
                suitability INTEGER NOT NULL,
                expected_profit INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
            """
        )

        # Databases created before history was owner-scoped predate this column.
        if "user_id" not in _columns(connection, "recommendation_history"):
            connection.execute("ALTER TABLE recommendation_history ADD COLUMN user_id INTEGER")

        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_history_user ON recommendation_history(user_id, id DESC)"
        )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")


def _public_user(row: sqlite3.Row | dict) -> dict:
    data = dict(row)
    data.pop("password_hash", None)
    return data


def create_user(user: UserCreate) -> dict:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO users (name, phone, password_hash, language, location)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user.name, user.phone, hash_password(user.password), user.language, user.location),
        )
        row = connection.execute(
            "SELECT id, name, phone, language, location, created_at FROM users WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    return _public_user(row)


def authenticate_user(phone: str, password: str) -> dict | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, name, phone, password_hash, language, location, created_at
            FROM users
            WHERE phone = ?
            """,
            (phone,),
        ).fetchone()

        if row is None:
            # Spend comparable time on unknown accounts so response latency does
            # not reveal which phone numbers are registered.
            verify_password(password, hash_password("timing-equalizer"))
            return None

        if not verify_password(password, row["password_hash"]):
            return None

        if needs_rehash(row["password_hash"]):
            connection.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (hash_password(password), row["id"]),
            )

    return _public_user(row)


def create_session(user_id: int) -> tuple[str, datetime]:
    token = generate_session_token()
    now = datetime.now(UTC)
    expires_at = now + timedelta(hours=get_settings().session_ttl_hours)
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (hash_session_token(token), user_id, now.isoformat(), expires_at.isoformat()),
        )
    return token, expires_at


def resolve_session(token: str) -> dict | None:
    now = datetime.now(UTC)
    with get_connection() as connection:
        connection.execute("DELETE FROM sessions WHERE expires_at < ?", (now.isoformat(),))
        row = connection.execute(
            """
            SELECT users.id, users.name, users.phone, users.language, users.location, users.created_at
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token_hash = ? AND sessions.expires_at >= ?
            """,
            (hash_session_token(token), now.isoformat()),
        ).fetchone()
    return _public_user(row) if row else None


def revoke_session(token: str) -> bool:
    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM sessions WHERE token_hash = ?", (hash_session_token(token),)
        )
    return cursor.rowcount > 0


def save_history_record(record: HistoryRecord, user_id: int) -> dict:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO recommendation_history
                (user_id, farmer_name, location, crop, suitability, expected_profit)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                record.farmer_name,
                record.location,
                record.crop,
                record.suitability,
                record.expected_profit,
            ),
        )
        row = connection.execute(
            """
            SELECT id, farmer_name, location, crop, suitability, expected_profit, created_at
            FROM recommendation_history
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
    return dict(row)


def list_history_records(user_id: int, limit: int = 25) -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, farmer_name, location, crop, suitability, expected_profit, created_at
            FROM recommendation_history
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def count_history_records() -> int:
    with get_connection() as connection:
        row = connection.execute("SELECT COUNT(*) AS total FROM recommendation_history").fetchone()
    return int(row["total"])


def count_users() -> int:
    with get_connection() as connection:
        row = connection.execute("SELECT COUNT(*) AS total FROM users").fetchone()
    return int(row["total"])
