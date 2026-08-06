import sqlite3
import hashlib
import secrets
from pathlib import Path

from .schemas import HistoryRecord, UserCreate

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DB_PATH = DATA_DIR / "annapurna_ai.sqlite"


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_database() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS recommendation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"{salt}${digest.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return secrets.compare_digest(candidate.hex(), digest)


def create_user(user: UserCreate) -> dict:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO users (name, phone, password_hash, language, location)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user.name, user.phone, _hash_password(user.password), user.language, user.location),
        )
        row = connection.execute(
            """
            SELECT id, name, phone, language, location, created_at
            FROM users
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
    return dict(row)


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
    if row is None or not _verify_password(password, row["password_hash"]):
        return None
    result = dict(row)
    result.pop("password_hash", None)
    return result


def save_history_record(record: HistoryRecord) -> dict:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO recommendation_history
                (farmer_name, location, crop, suitability, expected_profit)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
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


def list_history_records(limit: int = 25) -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, farmer_name, location, crop, suitability, expected_profit, created_at
            FROM recommendation_history
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
