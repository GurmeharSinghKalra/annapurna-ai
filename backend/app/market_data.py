"""Live mandi prices from the AGMARKNET dataset on data.gov.in, with cache and real trend.

Three things this module exists to fix:

1. **Commodity naming.** AGMARKNET filters are exact-match. "Rice" returns nothing; the dataset
   calls it ``Paddy(Dhan)(Common)``. Each crop therefore carries an ordered list of candidate
   official names, tried until one reports a price.
2. **Quota and latency.** The feed publishes roughly once a day and rate-limits callers. Prices are
   cached per (commodity, state, district) so a hundred farmers in one district cost one request,
   and a dated cached price is served when the feed is briefly unreachable.
3. **Trend.** The direction shown to a farmer is computed from stored observations. When there is
   not enough history to measure it, the API says so instead of returning an invented percentage.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .models import MarketPriceHistory, MarketPriceSnapshot

logger = logging.getLogger(__name__)

AGMARKNET_RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
AGMARKNET_RESOURCE_URL = f"https://api.data.gov.in/resource/{AGMARKNET_RESOURCE_ID}"

# AGMARKNET's own commodity spellings, most specific first. The crop name alone is kept last as a
# loose fallback for datasets that have been renamed upstream.
COMMODITY_CANDIDATES: dict[str, tuple[str, ...]] = {
    "Rice": ("Paddy(Dhan)(Common)", "Paddy(Dhan)(Basmati)", "Rice", "Paddy"),
    "Wheat": ("Wheat",),
    "Maize": ("Maize",),
    "Cotton": ("Kapas", "Cotton", "Cotton (Unginned)"),
    "Mustard": ("Mustard", "Mustard Oil", "Rapeseed & Mustard"),
    "Chickpea": ("Bengal Gram(Gram)(Whole)", "Bengal Gram Dal (Chana Dal)", "Gram", "Chickpea"),
    "Sugarcane": ("Sugarcane",),
    "Pearl Millet": ("Bajra(Pearl Millet/Cumbu)", "Bajra", "Pearl Millet"),
}

# Display names, used wherever the farmer sees the commodity rather than the crop.
DISPLAY_COMMODITY = {
    "Rice": "Paddy (common)",
    "Wheat": "Wheat",
    "Maize": "Maize",
    "Cotton": "Cotton (kapas)",
    "Mustard": "Mustard seed",
    "Chickpea": "Gram (chana)",
    "Sugarcane": "Sugarcane",
    "Pearl Millet": "Bajra",
}

_PRICE_KEYS = ("modal_price", "modal_price_per_quintal", "modalprice", "modal_price_rs_per_quintal", "price")
_MIN_KEYS = ("min_price", "min_price_per_quintal", "minprice")
_MAX_KEYS = ("max_price", "max_price_per_quintal", "maxprice")
_DATE_KEYS = ("arrival_date", "date", "reported_date", "updated_at", "reported_at")


class LiveMarketDataUnavailable(RuntimeError):
    """No official price could be verified for this crop and location."""


@dataclass(frozen=True)
class Scope:
    """Where a price applies. An empty district means the state-wide query was used."""

    commodity: str
    state: str
    district: str


def parse_location(location: str) -> tuple[str, str]:
    """Split the UI's ``District, State`` convention. Returns (state, district)."""
    parts = [part.strip() for part in (location or "").split(",") if part.strip()]
    if len(parts) >= 2:
        return parts[-1], parts[-2]
    if len(parts) == 1:
        return parts[0], ""
    return "", ""


def _normalise(record: dict) -> dict[str, Any]:
    return {str(k).strip().lower().replace(" ", "_").replace("-", "_"): v for k, v in record.items()}


def _records(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("records", "data", "results", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return [payload]


def _to_price(value: object) -> int | None:
    try:
        price = round(float(str(value).replace(",", "").strip()))
    except (TypeError, ValueError):
        return None
    # Mandi modal prices are INR/quintal. Anything outside this band is a unit or parsing error,
    # and passing it through would put a nonsense revenue figure in front of a farmer.
    return price if 10 <= price <= 500_000 else None


def _first_price(record: dict[str, Any], keys: tuple[str, ...]) -> int | None:
    for key in keys:
        price = _to_price(record.get(key))
        if price is not None:
            return price
    return None


def _match(records: list[dict], commodity: str) -> dict[str, Any] | None:
    """Pick the best record: exact commodity match first, then a substring match."""
    wanted = commodity.casefold()
    fallback: dict[str, Any] | None = None
    for raw in records:
        record = _normalise(raw)
        if _first_price(record, _PRICE_KEYS) is None:
            continue
        found = str(record.get("commodity") or record.get("crop") or "").casefold()
        if found == wanted:
            return record
        if fallback is None and (not found or wanted in found or found in wanted):
            fallback = record
    return fallback


async def _query_agmarknet(
    client: httpx.AsyncClient, commodity: str, state: str, district: str
) -> dict[str, Any] | None:
    params: dict[str, Any] = {
        "api-key": settings.agmarknet_api_key,
        "format": "json",
        "limit": 100,
        "filters[commodity]": commodity,
    }
    if state:
        params["filters[state]"] = state
    if district:
        params["filters[district]"] = district
    response = await client.get(AGMARKNET_RESOURCE_URL, params=params)
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError as exc:
        raise LiveMarketDataUnavailable("The mandi price service returned an unreadable response.") from exc
    return _match(_records(payload), commodity)


async def _fetch_live(crop: str, state: str, district: str) -> tuple[dict[str, Any], Scope]:
    """Try each official commodity spelling, narrowing from district to state to nationwide."""
    candidates = COMMODITY_CANDIDATES.get(crop, (crop,))
    scopes = [(state, district)] if district else []
    scopes.append((state, ""))
    if state:
        scopes.append(("", ""))

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(settings.market_timeout_seconds),
            headers={"Accept": "application/json", "User-Agent": "Annapurna-AI/1.0"},
        ) as client:
            for scope_state, scope_district in scopes:
                for commodity in candidates:
                    record = await _query_agmarknet(client, commodity, scope_state, scope_district)
                    if record:
                        return record, Scope(commodity, scope_state, scope_district)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in {401, 403}:
            raise LiveMarketDataUnavailable(
                "The mandi price key was rejected by data.gov.in. Check AGMARKNET_API_KEY."
            ) from exc
        if exc.response.status_code == 429:
            raise LiveMarketDataUnavailable(
                "The mandi price service is rate-limiting requests. Please try again shortly."
            ) from exc
        raise LiveMarketDataUnavailable("The mandi price service could not be reached.") from exc
    except httpx.HTTPError as exc:
        raise LiveMarketDataUnavailable("The mandi price service could not be reached.") from exc

    raise LiveMarketDataUnavailable(
        f"AGMARKNET is not reporting a current {DISPLAY_COMMODITY.get(crop, crop)} price for this location."
    )


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


async def _store(session: AsyncSession, crop: str, scope: Scope, record: dict[str, Any]) -> MarketPriceSnapshot:
    modal = _first_price(record, _PRICE_KEYS)
    assert modal is not None  # guaranteed by _match
    arrival = next((str(record[key]) for key in _DATE_KEYS if record.get(key)), None)

    snapshot = await session.scalar(
        select(MarketPriceSnapshot).where(
            MarketPriceSnapshot.commodity == scope.commodity,
            MarketPriceSnapshot.state == scope.state,
            MarketPriceSnapshot.district == scope.district,
        )
    )
    if snapshot is None:
        snapshot = MarketPriceSnapshot(commodity=scope.commodity, state=scope.state, district=scope.district)
        session.add(snapshot)
    snapshot.market = str(record.get("market") or "") or None
    snapshot.variety = str(record.get("variety") or "") or None
    snapshot.modal_price_per_quintal = modal
    snapshot.min_price_per_quintal = _first_price(record, _MIN_KEYS)
    snapshot.max_price_per_quintal = _first_price(record, _MAX_KEYS)
    snapshot.arrival_date = arrival
    snapshot.source = "AGMARKNET daily mandi price (data.gov.in)"
    snapshot.fetched_at = datetime.now(UTC)
    snapshot.payload = {k: str(v) for k, v in record.items()}

    if arrival:
        # One point per reporting day; re-reading the same day must not skew the trend.
        exists = await session.scalar(
            select(MarketPriceHistory.id).where(
                MarketPriceHistory.commodity == scope.commodity,
                MarketPriceHistory.state == scope.state,
                MarketPriceHistory.district == scope.district,
                MarketPriceHistory.arrival_date == arrival,
            )
        )
        if exists is None:
            session.add(
                MarketPriceHistory(
                    commodity=scope.commodity,
                    state=scope.state,
                    district=scope.district,
                    arrival_date=arrival,
                    modal_price_per_quintal=modal,
                    source="AGMARKNET daily mandi price (data.gov.in)",
                )
            )
    await session.commit()
    await session.refresh(snapshot)
    return snapshot


async def _trend(session: AsyncSession, scope: Scope, latest_price: int) -> tuple[float | None, str]:
    """Measure direction against observations from the preceding fortnight."""
    since = datetime.now(UTC) - timedelta(days=settings.market_trend_window_days)
    rows = (
        await session.scalars(
            select(MarketPriceHistory)
            .where(
                MarketPriceHistory.commodity == scope.commodity,
                MarketPriceHistory.state == scope.state,
                MarketPriceHistory.district == scope.district,
                MarketPriceHistory.observed_at >= since,
            )
            .order_by(MarketPriceHistory.observed_at.asc())
        )
    ).all()
    earlier = [row.modal_price_per_quintal for row in rows[:-1] if row.modal_price_per_quintal > 0]
    if len(earlier) < settings.market_trend_min_points:
        return None, "not enough recorded history yet"
    baseline = sum(earlier) / len(earlier)
    if baseline <= 0:
        return None, "not enough recorded history yet"
    percent = round(((latest_price - baseline) / baseline) * 100, 1)
    if percent > 1:
        return percent, "rising"
    if percent < -1:
        return percent, "softening"
    return percent, "steady"


def _profile(
    crop: str,
    snapshot: MarketPriceSnapshot,
    trend_percent: float | None,
    trend_label: str,
    source: str,
    note: str,
) -> dict[str, Any]:
    return {
        "source": source,
        "crop": crop,
        "commodity": DISPLAY_COMMODITY.get(crop, crop),
        "official_commodity": snapshot.commodity,
        "modal_price_per_quintal": snapshot.modal_price_per_quintal,
        "min_price_per_quintal": snapshot.min_price_per_quintal,
        "max_price_per_quintal": snapshot.max_price_per_quintal,
        "trend_percent": trend_percent,
        "trend": trend_label,
        "state": snapshot.state or "all states",
        "district": snapshot.district or "all districts",
        "market": snapshot.market or "market not reported",
        "variety": snapshot.variety or "variety not reported",
        "observed_at": snapshot.arrival_date or "date not reported",
        "fetched_at": _aware(snapshot.fetched_at).isoformat(),
        "note": note,
    }


async def market_price(session: AsyncSession, crop: str, location: str) -> dict[str, Any]:
    """Return a dated official mandi price for this crop and location.

    Raises LiveMarketDataUnavailable when no key is configured and nothing is cached, so the
    caller can decide between a 503 and a clearly-labelled planning baseline.
    """
    state, district = parse_location(location)
    cached = await _cached(session, crop, state, district)

    if cached is not None:
        age = datetime.now(UTC) - _aware(cached.fetched_at)
        if age < timedelta(minutes=settings.market_cache_ttl_minutes):
            scope = Scope(cached.commodity, cached.state, cached.district)
            percent, label = await _trend(session, scope, cached.modal_price_per_quintal)
            return _profile(
                crop,
                cached,
                percent,
                label,
                cached.source,
                "Official daily wholesale mandi price. Confirm today's rate at your own mandi before selling.",
            )

    if not settings.agmarknet_api_key:
        if cached is not None:
            return await _stale(session, crop, cached, "no mandi API key is configured")
        raise LiveMarketDataUnavailable("Live mandi prices need AGMARKNET_API_KEY (a free key from data.gov.in).")

    try:
        record, scope = await _fetch_live(crop, state, district)
    except LiveMarketDataUnavailable as exc:
        if cached is not None:
            return await _stale(session, crop, cached, str(exc))
        raise

    snapshot = await _store(session, crop, scope, record)
    percent, label = await _trend(session, scope, snapshot.modal_price_per_quintal)
    return _profile(
        crop,
        snapshot,
        percent,
        label,
        snapshot.source,
        "Official daily wholesale mandi price. Confirm today's rate at your own mandi before selling.",
    )


async def _cached(session: AsyncSession, crop: str, state: str, district: str) -> MarketPriceSnapshot | None:
    """Most specific cached row for this crop: district, then state, then nationwide."""
    candidates = COMMODITY_CANDIDATES.get(crop, (crop,))
    for scope_state, scope_district in ((state, district), (state, ""), ("", "")):
        row = await session.scalar(
            select(MarketPriceSnapshot)
            .where(
                MarketPriceSnapshot.commodity.in_(candidates),
                MarketPriceSnapshot.state == scope_state,
                MarketPriceSnapshot.district == scope_district,
            )
            .order_by(MarketPriceSnapshot.fetched_at.desc())
        )
        if row is not None:
            return row
    return None


async def _stale(session: AsyncSession, crop: str, cached: MarketPriceSnapshot, reason: str) -> dict[str, Any]:
    scope = Scope(cached.commodity, cached.state, cached.district)
    percent, label = await _trend(session, scope, cached.modal_price_per_quintal)
    age_hours = int((datetime.now(UTC) - _aware(cached.fetched_at)).total_seconds() // 3600)
    return _profile(
        crop,
        cached,
        percent,
        label,
        f"AGMARKNET cached price ({age_hours}h old)",
        f"Showing the last price Annapurna retrieved, because {reason}. Confirm the current rate at your mandi.",
    )


async def prices_for(
    session: AsyncSession, crops: list[str], location: str, refresh_limit: int = 4
) -> tuple[dict[str, int], list[str]]:
    """Resolve mandi prices for several crops at once.

    Returns (prices_by_crop, notes). Ranking every crop would otherwise mean one upstream request
    per crop on every page load, so cached rows are used freely and at most ``refresh_limit`` crops
    trigger a live request per call. Crops without a price simply fall back to their reference
    price in the recommender, which labels itself as an MSP.
    """
    prices: dict[str, int] = {}
    notes: list[str] = []
    state, district = parse_location(location)
    refreshed = 0

    for crop in crops:
        cached = await _cached(session, crop, state, district)
        fresh = cached is not None and (
            datetime.now(UTC) - _aware(cached.fetched_at) < timedelta(minutes=settings.market_cache_ttl_minutes)
        )
        if fresh and cached is not None:
            prices[crop] = cached.modal_price_per_quintal
            continue

        if not settings.agmarknet_api_key:
            if cached is not None:
                prices[crop] = cached.modal_price_per_quintal
            continue

        if refreshed >= refresh_limit:
            if cached is not None:
                prices[crop] = cached.modal_price_per_quintal
            continue

        refreshed += 1
        try:
            record, scope = await _fetch_live(crop, state, district)
        except LiveMarketDataUnavailable as exc:
            if cached is not None:
                prices[crop] = cached.modal_price_per_quintal
            else:
                notes.append(f"{crop}: {exc}")
            continue
        snapshot = await _store(session, crop, scope, record)
        prices[crop] = snapshot.modal_price_per_quintal

    return prices, notes
