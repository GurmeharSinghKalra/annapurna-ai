"""Accounts and the records they own."""

from __future__ import annotations


def test_register_login_and_me(client, account):
    assert account["farmer"]["phone"] == "9876543210"
    assert client.get("/auth/me", headers=account["headers"]).status_code == 200
    login = client.post("/auth/login", json={"phone": "9876543210", "password": account["password"]})
    assert login.status_code == 200
    assert login.json()["farmer"]["id"] == account["farmer"]["id"]


def test_phone_is_normalised_so_one_number_is_one_account(client, account):
    """+91 98765-43210, 09876543210 and 9876543210 must not become three accounts."""
    for variant in ("+91 98765-43210", "09876543210", "9876543210", "+919876543210"):
        duplicate = client.post("/auth/register", json={"name": "X", "phone": variant, "password": "anotherpass1"})
        assert duplicate.status_code == 409, variant
        login = client.post("/auth/login", json={"phone": variant, "password": account["password"]})
        assert login.status_code == 200, variant


def test_bad_credentials_do_not_reveal_whether_the_account_exists(client, account):
    unknown = client.post("/auth/login", json={"phone": "9000000001", "password": "whatever1"})
    wrong = client.post("/auth/login", json={"phone": account["phone"], "password": "wrongpass1"})
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"]


def test_weak_passwords_are_refused(client):
    for password in ("short", "12345678", ""):
        response = client.post("/auth/register", json={"name": "A", "phone": "9000000002", "password": password})
        assert response.status_code == 422, password


def test_invalid_phone_numbers_are_refused(client):
    for phone in ("1234567890", "98765", "abcdefghij", "+1 555 123 4567"):
        response = client.post("/auth/register", json={"name": "A", "phone": phone, "password": "goodpass123"})
        assert response.status_code == 422, phone


def test_protected_routes_require_a_token(client):
    for method, path in [("get", "/auth/me"), ("get", "/plans"), ("get", "/finance/plans"), ("get", "/profiles")]:
        assert getattr(client, method)(path).status_code == 401, path


def test_a_garbage_token_is_rejected_not_accepted(client):
    headers = {"Authorization": "Bearer not.a.real.token"}
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_refresh_rotates_and_a_replayed_token_revokes_the_session(client, account):
    rotated = client.post("/auth/refresh", json={"refresh_token": account["refresh_token"]})
    assert rotated.status_code == 200
    new_token = rotated.json()["refresh_token"]
    assert new_token != account["refresh_token"]

    # Replaying a spent token means it leaked, so every session for the account is dropped.
    assert client.post("/auth/refresh", json={"refresh_token": account["refresh_token"]}).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": new_token}).status_code == 401


def test_logout_invalidates_the_refresh_token(client, account):
    assert client.post("/auth/logout", json={"refresh_token": account["refresh_token"]}).status_code == 204
    assert client.post("/auth/refresh", json={"refresh_token": account["refresh_token"]}).status_code == 401


def test_changing_the_password_ends_other_sessions(client, account):
    changed = client.post(
        "/auth/password",
        headers=account["headers"],
        json={"current_password": account["password"], "new_password": "brandnewpass456"},
    )
    assert changed.status_code == 204
    assert client.post("/auth/refresh", json={"refresh_token": account["refresh_token"]}).status_code == 401
    assert (
        client.post("/auth/login", json={"phone": account["phone"], "password": "brandnewpass456"}).status_code == 200
    )


def test_a_wrong_current_password_cannot_change_the_password(client, account):
    response = client.post(
        "/auth/password",
        headers=account["headers"],
        json={"current_password": "nottherightone", "new_password": "brandnewpass456"},
    )
    assert response.status_code == 400


def _saved_plan(client, account, farm):
    recommendation = client.post("/recommendations", json=farm).json()["recommendations"][0]
    return client.post(
        "/plans",
        headers=account["headers"],
        json={"farm": farm, "recommendation": recommendation, "note": "kharif plan"},
    )


def test_plans_round_trip(client, account, farm):
    created = _saved_plan(client, account, farm)
    assert created.status_code == 201
    plan_id = created.json()["id"]

    listing = client.get("/plans", headers=account["headers"]).json()
    assert listing["total"] == 1
    assert listing["items"][0]["note"] == "kharif plan"

    fetched = client.get(f"/plans/{plan_id}", headers=account["headers"])
    assert fetched.status_code == 200
    # The snapshot must be self-contained, so an old plan still reads correctly later.
    assert fetched.json()["farm_snapshot"]["location"] == farm["location"]
    assert fetched.json()["recommendation"]["crop"] == created.json()["crop"]

    assert client.delete(f"/plans/{plan_id}", headers=account["headers"]).status_code == 204
    assert client.get(f"/plans/{plan_id}", headers=account["headers"]).status_code == 404


def test_one_account_cannot_read_or_delete_another_accounts_plan(client, account, farm):
    plan_id = _saved_plan(client, account, farm).json()["id"]
    other = client.post(
        "/auth/register", json={"name": "Other", "phone": "9000000009", "password": "otherpass123"}
    ).json()
    headers = {"Authorization": f"Bearer {other['access_token']}"}

    assert client.get(f"/plans/{plan_id}", headers=headers).status_code == 404
    assert client.delete(f"/plans/{plan_id}", headers=headers).status_code == 404
    assert client.get("/plans", headers=headers).json()["total"] == 0
    # ...and the owner still has it.
    assert client.get(f"/plans/{plan_id}", headers=account["headers"]).status_code == 200


def test_plan_listing_paginates(client, account, farm):
    recommendation = client.post("/recommendations", json=farm).json()["recommendations"][0]
    for index in range(5):
        client.post(
            "/plans",
            headers=account["headers"],
            json={"farm": farm, "recommendation": recommendation, "note": f"plan {index}"},
        )
    page = client.get("/plans?limit=2&offset=0", headers=account["headers"]).json()
    assert page["total"] == 5 and len(page["items"]) == 2
    assert len(client.get("/plans?limit=2&offset=4", headers=account["headers"]).json()["items"]) == 1


def test_finance_plans_upsert_per_crop_rather_than_duplicating(client, account, farm):
    plan = client.post("/finance/season-plan", json={"farm": farm, "crop": "Maize"}).json()
    for _ in range(3):
        saved = client.post("/finance/plans", headers=account["headers"], json={"farm": farm, "plan": plan})
        assert saved.status_code == 201
    assert len(client.get("/finance/plans", headers=account["headers"]).json()) == 1


def test_farm_profiles_round_trip_and_enforce_one_default(client, account, farm):
    first = client.put(
        "/profiles", headers=account["headers"], json={"label": "North field", "farm": farm, "is_default": True}
    )
    assert first.status_code == 200
    second = client.put(
        "/profiles", headers=account["headers"], json={"label": "South field", "farm": farm, "is_default": True}
    )
    assert second.status_code == 200
    profiles = client.get("/profiles", headers=account["headers"]).json()
    assert len(profiles) == 2
    assert sum(1 for item in profiles if item["is_default"]) == 1


def test_deleting_an_account_removes_everything_it_owns(client, account, farm):
    plan_id = _saved_plan(client, account, farm).json()["id"]
    assert client.delete("/auth/me", headers=account["headers"]).status_code == 204
    # The token no longer resolves to a farmer, and the row is gone with them.
    assert client.get(f"/plans/{plan_id}", headers=account["headers"]).status_code == 401
    assert (
        client.post("/auth/login", json={"phone": account["phone"], "password": account["password"]}).status_code == 401
    )


def test_planning_routes_work_without_an_account(client, farm):
    """Accounts must remain optional: an anonymous farmer loses storage, not the product."""
    assert client.post("/recommendations", json=farm).status_code == 200
    assert client.post("/analysis", json=farm).status_code == 200
    assert client.post("/finance/season-plan", json={"farm": farm}).status_code == 200
    assert client.post("/soil", json=farm).status_code == 200
