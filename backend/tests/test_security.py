"""Regression tests for the vulnerabilities found in the audit.

Each name says what used to be possible.
"""

from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from app.deps import SlidingWindowLimiter


def png_bytes(size=(8, 8)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, (70, 130, 50)).save(buffer, format="PNG")
    return buffer.getvalue()


# --------------------------------------------------------------------- PDF report


def forged_recommendation(**overrides) -> dict:
    band = {"low": 1, "typical": 2, "high": 3}
    payload = {
        "crop": "Rice",
        "suitability": 100,
        "verdict": "strong match",
        "reasons": ["believe me"],
        "cautions": ["none at all"],
        "expected_profit": 99_999_999,
        "expected_yield": 999.0,
        "estimated_cost": 1,
        "estimated_revenue": 99_999_999,
        "profit_margin": 99,
        "market_price": 99_999,
        "price_basis": "trust me",
        "duration_days": 1,
        "sustainability_score": 100,
        "water": "Low",
        "rotation": "x",
        "sustainability": "x",
        "advisory": "x",
        "economics": dict.fromkeys(
            ("expected_yield_quintal", "estimated_cost_inr", "estimated_revenue_inr", "expected_profit_inr"), band
        ),
    }
    payload.update(overrides)
    return payload


def test_pdf_does_not_execute_reportlab_markup_from_the_client(client, farm):
    """`<img src="/etc/passwd"/>` in a reason used to make the server read that file into the PDF."""
    attack = forged_recommendation(reasons=['<img src="/etc/passwd" valign="top"/>LEAK'])
    response = client.post("/reports/pdf", json={"farm": farm, "recommendation": attack})
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")


def test_unbalanced_markup_no_longer_returns_a_500(client, farm):
    attack = forged_recommendation(cautions=["<b>never closed"])
    assert client.post("/reports/pdf", json={"farm": farm, "recommendation": attack}).status_code == 200


def test_the_pdf_shows_the_servers_numbers_not_the_clients(client, farm):
    """Anyone could previously produce a branded Annapurna PDF claiming any profit they liked."""
    response = client.post("/reports/pdf", json={"farm": farm, "recommendation": forged_recommendation()})
    assert response.status_code == 200
    assert b"99,999,999" not in response.content


def test_the_pdf_refuses_a_crop_outside_the_catalogue(client, farm):
    response = client.post("/reports/pdf", json={"farm": farm, "crop": "Unobtainium"})
    assert response.status_code == 422
    assert "Unobtainium" in response.json()["detail"]


def test_the_pdf_still_works_for_a_real_request(client, farm):
    response = client.post("/reports/pdf", json={"farm": farm, "crop": "Maize"})
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")
    assert "maize" in response.headers["content-disposition"]


# --------------------------------------------------------------------- request size


def test_an_oversized_json_body_is_rejected(client, farm):
    bloated = {"farm": farm, "crop": "Maize", "finance": {"expenses": [{"category": "x" * 300} for _ in range(4000)]}}
    assert client.post("/reports/pdf", json=bloated).status_code == 413


def test_a_chunked_body_cannot_bypass_the_upload_limit(client):
    """With no Content-Length the declared-size guard simply did not apply, and the body was
    buffered into the process without any ceiling."""

    def stream():
        for _ in range(40):
            yield b"x" * (512 * 1024)  # 20 MB, chunked

    response = client.post("/disease", content=stream(), headers={"content-type": "multipart/form-data; boundary=zz"})
    assert response.status_code == 413


def test_a_declared_oversized_upload_is_rejected_before_parsing(client):
    response = client.post(
        "/disease",
        content=b"tiny",
        headers={"content-type": "multipart/form-data; boundary=zz", "content-length": str(64 * 1024 * 1024)},
    )
    assert response.status_code == 413


# --------------------------------------------------------------------- image upload


def test_non_image_bytes_are_rejected_even_when_the_mime_type_lies(client):
    response = client.post("/disease", files={"file": ("leaf.png", b"this is not an image", "image/png")})
    assert response.status_code == 422


def test_an_unsupported_content_type_is_rejected(client):
    response = client.post("/disease", files={"file": ("leaf.gif", png_bytes(), "image/gif")})
    assert response.status_code == 415


def test_an_empty_upload_is_rejected(client):
    response = client.post("/disease", files={"file": ("leaf.png", b"", "image/png")})
    assert response.status_code in {400, 422}


def test_screening_refuses_rather_than_inventing_a_diagnosis(client):
    """It used to return 'leaf stress detected' at 0.72 confidence for any image at all."""
    response = client.post("/disease", files={"file": ("leaf.png", png_bytes(), "image/png")})
    assert response.status_code == 503
    detail = response.json()["detail"]
    assert "GEMINI_API_KEY" in detail
    assert "leaf stress" not in detail.lower()


# --------------------------------------------------------------------- secrets and CORS


def test_no_route_leaks_configured_feed_urls_or_credentials(client, farm):
    """`/market` and `/analysis` used to echo AGMARKNET_SOURCE_URL, including any embedded token."""
    for response in (
        client.get("/integrations/status"),
        client.get("/admin/summary"),
        client.get("/health"),
        client.post("/analysis", json=farm),
    ):
        body = response.text.lower()
        for secret in ("api-key", "apikey", "api_key=", "password", "jwt_secret", "sslmode"):
            assert secret not in body, f"{response.url} leaked {secret}"


def test_cors_allows_the_local_frontend_without_credentials(client):
    response = client.options(
        "/analysis",
        headers={"Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": "POST"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    # Tokens travel in a header, so cookies must never be allowed across origins.
    assert response.headers.get("access-control-allow-credentials") is None


def test_an_unlisted_origin_is_not_echoed_back(client):
    response = client.options(
        "/analysis",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert response.headers.get("access-control-allow-origin") != "https://evil.example"


# --------------------------------------------------------------------- rate limiting


def test_the_limiter_blocks_once_the_window_is_full():
    limiter = SlidingWindowLimiter()
    for _ in range(3):
        allowed, _ = limiter.check("client", limit=3, window_seconds=60)
        assert allowed
    allowed, retry_after = limiter.check("client", limit=3, window_seconds=60)
    assert not allowed
    assert retry_after > 0


def test_the_limiter_counts_each_client_separately():
    limiter = SlidingWindowLimiter()
    assert limiter.check("a", limit=1, window_seconds=60)[0]
    assert not limiter.check("a", limit=1, window_seconds=60)[0]
    assert limiter.check("b", limit=1, window_seconds=60)[0]


def test_ai_routes_are_rate_limited(client, farm, monkeypatch):
    from app import main

    monkeypatch.setitem(main.app.dependency_overrides, object(), object())  # no-op, keeps intent clear
    from app.deps import limiter

    limiter._hits.clear()
    # Drive the shared limiter straight to its ceiling for the AI bucket.
    from app.config import settings

    for _ in range(settings.ai_rate_limit_per_hour + 1):
        limiter.check("ai:ip:testclient", settings.ai_rate_limit_per_hour, 3600)
    response = client.post("/chat", json={"question": "Will this be limited?", "farm": farm})
    assert response.status_code == 429
    assert response.headers.get("Retry-After")


# --------------------------------------------------------------------- error handling


def test_validation_errors_are_422_with_a_usable_message(client):
    response = client.post("/analysis", json={"season": "Monsoon", "soil_type": "Unknown"})
    assert response.status_code == 422
    assert response.json()["detail"]


def test_every_response_carries_a_request_id(client):
    assert client.get("/health").headers.get("X-Request-ID")


def test_removed_prototype_routes_are_gone(client):
    """The old SQLite auth/history prototype must not be reachable."""
    assert client.post("/auth/register", json={}).status_code == 422  # exists, but validates
    assert client.get("/history").status_code == 404


@pytest.mark.parametrize(
    "finance",
    [
        {"summary": [1, 2, 3]},
        {"summary": {}, "expenses": ["a", "b"]},
        {"scenarios": ["x"]},
        {"expenses": [1, 2]},
        {"summary": "not a mapping"},
        [1, 2, 3],
        "a string",
    ],
)
def test_a_malformed_finance_payload_cannot_500_the_pdf(client, farm, finance):
    """`finance` is a free-form dict, so a caller can put a list where a mapping belongs.
    Four such shapes used to reach a `.get` on an int and return a 500."""
    response = client.post("/reports/pdf", json={"farm": farm, "crop": "Maize", "finance": finance})
    assert response.status_code in {200, 422}, response.text
    if response.status_code == 200:
        assert response.content.startswith(b"%PDF-")
