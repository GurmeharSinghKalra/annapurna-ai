"""Authentication, sessions, ownership, and throttling."""

import pytest

from app.security import hash_password, needs_rehash, verify_password


def test_register_issues_a_session_token(client):
    response = client.post(
        "/auth/register",
        json={"name": "A Farmer", "phone": "9811100001", "password": "secret1234"},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]
    assert "password" not in payload["user"]
    assert "password_hash" not in payload["user"]


def test_duplicate_phone_is_rejected(client, registered):
    registered(phone="9811100001")
    response = client.post(
        "/auth/register",
        json={"name": "Someone Else", "phone": "9811100001", "password": "secret1234"},
    )
    assert response.status_code == 409


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "A", "phone": "9811100001", "password": "short"},  # under 8 characters
        {"name": "A", "phone": "12345", "password": "secret1234"},  # not 10 digits
        {"name": "", "phone": "9811100001", "password": "secret1234"},  # empty name
        {"name": "A", "phone": "9811100001", "password": "secret1234", "role": "admin"},  # extra field
    ],
)
def test_registration_input_is_validated(client, payload):
    assert client.post("/auth/register", json=payload).status_code == 422


def test_login_round_trip(client, registered):
    _, user, password = registered()
    response = client.post("/auth/login", json={"phone": user["phone"], "password": password})
    assert response.status_code == 200
    assert response.json()["user"]["phone"] == user["phone"]
    assert response.json()["access_token"]


@pytest.mark.parametrize("password", ["wrong-password", "secret1235"])
def test_login_with_a_bad_password_is_rejected(client, registered, password):
    _, user, _ = registered()
    response = client.post("/auth/login", json={"phone": user["phone"], "password": password})
    assert response.status_code == 401


def test_login_for_an_unknown_phone_is_rejected(client):
    response = client.post("/auth/login", json={"phone": "9999999999", "password": "secret1234"})
    assert response.status_code == 401


def test_me_requires_a_valid_token(client, registered):
    headers, user, _ = registered()
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer nonsense"}).status_code == 401
    assert client.get("/auth/me", headers=headers).json()["user"]["id"] == user["id"]


def test_logout_revokes_the_session(client, registered):
    headers, _, _ = registered()
    assert client.get("/auth/me", headers=headers).status_code == 200
    assert client.post("/auth/logout", headers=headers).status_code == 204
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_repeated_failures_are_throttled(client, registered):
    _, user, _ = registered()
    statuses = [
        client.post("/auth/login", json={"phone": user["phone"], "password": f"bad{i}"}).status_code
        for i in range(8)
    ]
    assert statuses[:5] == [401] * 5, "first attempts should be plain rejections"
    assert 429 in statuses, "the limiter must engage before unlimited guessing"


def test_a_successful_login_clears_the_throttle(client, registered):
    _, user, password = registered()
    for _ in range(3):
        client.post("/auth/login", json={"phone": user["phone"], "password": "wrong"})
    assert client.post("/auth/login", json={"phone": user["phone"], "password": password}).status_code == 200
    # The counter reset, so a fresh run of failures is not immediately throttled.
    assert client.post("/auth/login", json={"phone": user["phone"], "password": "wrong"}).status_code == 401


# ----- password hashing ---------------------------------------------------- #


def test_password_hash_round_trip():
    stored = hash_password("secret1234", iterations=1000)
    assert verify_password("secret1234", stored)
    assert not verify_password("secret1235", stored)
    assert "secret1234" not in stored


def test_legacy_hashes_still_verify_and_are_flagged_for_rehash():
    import hashlib

    salt = "a" * 32
    digest = hashlib.pbkdf2_hmac("sha256", b"secret1234", salt.encode(), 100_000).hex()
    legacy = f"{salt}${digest}"

    assert verify_password("secret1234", legacy)
    assert not verify_password("wrong", legacy)
    assert needs_rehash(legacy)


def test_login_upgrades_a_legacy_hash(client, registered):
    import hashlib

    from app.database import get_connection

    _, user, _ = registered()
    salt = "b" * 32
    digest = hashlib.pbkdf2_hmac("sha256", b"secret1234", salt.encode(), 100_000).hex()
    with get_connection() as connection:
        connection.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?", (f"{salt}${digest}", user["id"])
        )

    assert client.post("/auth/login", json={"phone": user["phone"], "password": "secret1234"}).status_code == 200

    with get_connection() as connection:
        stored = connection.execute(
            "SELECT password_hash FROM users WHERE id = ?", (user["id"],)
        ).fetchone()["password_hash"]
    assert not needs_rehash(stored), "a legacy hash should be upgraded on successful login"


def test_malformed_hashes_never_authenticate():
    for stored in ["", "no-delimiter", "a$b$c", "pbkdf2_sha256$notanint$salt$digest"]:
        assert not verify_password("secret1234", stored)
