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
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .models import MarketPriceHistory, MarketPriceSnapshot

logger = logging.getLogger(__name__)

AGMARKNET_RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
AGMARKNET_RESOURCE_URL = f"https://api.data.gov.in/resource/{AGMARKNET_RESOURCE_ID}"
AGMARKNET_SOURCE = "AGMARKNET daily mandi price (data.gov.in)"

# A keyless community mirror of the same government dataset, used when no AGMARKNET key is
# configured so the product shows real prices with zero setup. Its coverage is narrower than the
# official feed, so the official one always wins when a key exists.
KEYLESS_SOURCE = "Community mirror of AGMARKNET (mandi-api)"
KEYLESS_URL = "https://mandi-api.onrender.com/v1/prices"
KEYLESS_STATES = frozenset({"Maharashtra", "Uttar Pradesh", "Punjab", "Madhya Pradesh", "Karnataka"})

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


# Remembers (crop, state, district) lookups that found nothing, so a crop the feed does not cover
# is not re-requested on every analysis. Short-lived: a crop out of season now will be in season
# later, and the keyless mirror shares one rate limit across all its users.
_misses: dict[tuple[str, str, str], tuple[float, str]] = {}


def _miss_key(crop: str, state: str, district: str) -> tuple[str, str, str]:
    return (crop, state.casefold(), district.casefold())


def _recent_miss(crop: str, state: str, district: str) -> str | None:
    entry = _misses.get(_miss_key(crop, state, district))
    if entry is None:
        return None
    recorded_at, reason = entry
    if time.monotonic() - recorded_at > settings.market_miss_ttl_seconds:
        _misses.pop(_miss_key(crop, state, district), None)
        return None
    return reason


def _record_miss(crop: str, state: str, district: str, reason: str) -> None:
    if len(_misses) > 5_000:
        _misses.clear()
    _misses[_miss_key(crop, state, district)] = (time.monotonic(), reason)


def clear_miss_cache() -> None:
    """Forget remembered lookup failures. Used by tests."""
    _misses.clear()


@dataclass(frozen=True)
class Scope:
    """Where a price applies, and which provider produced it.

    An empty district means the state-wide query was used.
    """

    commodity: str
    state: str
    district: str
    source: str = AGMARKNET_SOURCE


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
    except (TypeError, ValueError, OverflowError):
        # float("1e400") is inf, and round(inf) raises OverflowError rather than ValueError.
        return None
    if price != price or price in (float("inf"), float("-inf")):
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


# Feeds report arrival dates in several formats and do not agree on ordering.
_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d %b %Y", "%d-%b-%Y")


def parse_arrival_date(value: object) -> date | None:
    """Parse a feed's arrival date, or None when it is absent or unrecognised."""
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:  # ISO-8601 with a time component
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _record_date(record: dict[str, Any]) -> date | None:
    for key in _DATE_KEYS:
        parsed = parse_arrival_date(record.get(key))
        if parsed is not None:
            return parsed
    return None


def _match(records: list[dict], commodity: str) -> dict[str, Any] | None:
    """Pick the most recent record for this commodity, preferring an exact name match.

    A page from the feed mixes commodities and dates in no guaranteed order, so taking the first
    record that happened to parse could quote a price from weeks ago, or from a different
    commodity whose name merely overlapped. Exact matches beat partial ones, and within each
    group the newest arrival date wins.
    """
    wanted = commodity.casefold()
    exact: list[tuple[date | None, dict[str, Any]]] = []
    partial: list[tuple[date | None, dict[str, Any]]] = []

    for raw in records:
        record = _normalise(raw)
        if _first_price(record, _PRICE_KEYS) is None:
            continue
        found = str(record.get("commodity") or record.get("crop") or "").casefold()
        entry = (_record_date(record), record)
        if found == wanted:
            exact.append(entry)
        elif not found or wanted in found or found in wanted:
            partial.append(entry)

    for group in (exact, partial):
        if group:
            # date.min for undated rows, so a dated row always outranks an undated one.
            return max(group, key=lambda item: item[0] or date.min)[1]
    return None


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


def _keyless_state(state: str) -> str | None:
    """Match the farmer's state to the mirror's supported list, ignoring case and spacing."""
    wanted = " ".join(state.split()).casefold()
    for supported in KEYLESS_STATES:
        if supported.casefold() == wanted:
            return supported
    return None


async def _query_keyless(client: httpx.AsyncClient, commodity: str, state: str) -> dict[str, Any] | None:
    response = await client.get(KEYLESS_URL, params={"state": state, "commodity": commodity})
    if response.status_code == 404:
        return None
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError as exc:
        raise LiveMarketDataUnavailable("The mandi price service returned an unreadable response.") from exc
    if isinstance(payload, dict) and payload.get("success") is False:
        return None
    return _match(_records(payload), commodity)


async def _fetch_keyless(crop: str, state: str) -> tuple[dict[str, Any], Scope]:
    """Fetch from the keyless mirror. Only some states are covered."""
    supported = _keyless_state(state)
    if supported is None:
        raise LiveMarketDataUnavailable(
            f"Live mandi prices for {state or 'this location'} need AGMARKNET_API_KEY "
            f"(a free key from data.gov.in). The keyless source covers only "
            f"{', '.join(sorted(KEYLESS_STATES))}."
        )
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(settings.market_timeout_seconds),
            headers={"Accept": "application/json", "User-Agent": "Annapurna-AI/1.0"},
        ) as client:
            for commodity in COMMODITY_CANDIDATES.get(crop, (crop,)):
                record = await _query_keyless(client, commodity, supported)
                if record:
                    return record, Scope(commodity, supported, "", KEYLESS_SOURCE)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 429:
            raise LiveMarketDataUnavailable(
                "The keyless mandi source is rate-limiting requests. Configure AGMARKNET_API_KEY "
                "for a dedicated quota, or try again shortly."
            ) from exc
        raise LiveMarketDataUnavailable("The keyless mandi source could not be reached.") from exc
    except httpx.HTTPError as exc:
        raise LiveMarketDataUnavailable("The keyless mandi source could not be reached.") from exc

    raise LiveMarketDataUnavailable(
        f"No current {DISPLAY_COMMODITY.get(crop, crop)} price is being reported for {supported}."
    )


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
                        return record, Scope(commodity, scope_state, scope_district, AGMARKNET_SOURCE)
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
    snapshot.source = scope.source
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
                    source=scope.source,
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
        # A state-wide query still returns a specific mandi, so show the district it reported
        # rather than the (empty) query scope.
        "district": snapshot.district or (snapshot.payload or {}).get("district") or "all districts",
        "market": snapshot.market or "market not reported",
        "variety": snapshot.variety or "variety not reported",
        "observed_at": snapshot.arrival_date or "date not reported",
        "fetched_at": _aware(snapshot.fetched_at).isoformat(),
        "note": note,
    }


def _price_note(source: str) -> str:
    if source.startswith(KEYLESS_SOURCE):
        return (
            "Daily wholesale mandi price from a community mirror of the government dataset. "
            "Confirm today's rate at your own mandi before selling."
        )
    return "Official daily wholesale mandi price. Confirm today's rate at your own mandi before selling."


async def fetch_from_best_provider(crop: str, state: str, district: str) -> tuple[dict[str, Any], Scope]:
    """Official feed when a key is configured, otherwise the keyless mirror.

    The official feed covers every state and gives a dedicated quota, so a configured key always
    wins. Without one the mirror still provides real prices for the states it covers, which beats
    falling straight back to a support price.
    """
    remembered = _recent_miss(crop, state, district)
    if remembered is not None:
        raise LiveMarketDataUnavailable(remembered)

    if not settings.agmarknet_api_key and not settings.keyless_market_fallback:
        raise LiveMarketDataUnavailable("Live mandi prices need AGMARKNET_API_KEY (a free key from data.gov.in).")

    try:
        if settings.agmarknet_api_key:
            return await _fetch_live(crop, state, district)
        return await _fetch_keyless(crop, state)
    except LiveMarketDataUnavailable as exc:
        # Remember the failure, so a crop this feed never reports does not spend a fresh upstream
        # request on every analysis.
        _record_miss(crop, state, district, str(exc))
        raise


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
            scope = Scope(cached.commodity, cached.state, cached.district, cached.source)
            percent, label = await _trend(session, scope, cached.modal_price_per_quintal)
            return _profile(crop, cached, percent, label, cached.source, _price_note(cached.source))

    try:
        record, scope = await fetch_from_best_provider(crop, state, district)
    except LiveMarketDataUnavailable as exc:
        if cached is not None:
            return await _stale(session, crop, cached, str(exc))
        raise

    snapshot = await _store(session, crop, scope, record)
    percent, label = await _trend(session, scope, snapshot.modal_price_per_quintal)
    return _profile(crop, snapshot, percent, label, snapshot.source, _price_note(snapshot.source))


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
    """Serve the last price we retrieved, saying plainly how old it is and who published it.

    The source is read back from the cached row rather than assumed. Labelling a cached
    community-mirror price as "AGMARKNET" would attribute it to a feed it never came from,
    which is exactly the kind of quiet mislabelling this product exists not to do.
    """
    scope = Scope(cached.commodity, cached.state, cached.district, cached.source)
    percent, label = await _trend(session, scope, cached.modal_price_per_quintal)
    age_hours = int((datetime.now(UTC) - _aware(cached.fetched_at)).total_seconds() // 3600)
    return _profile(
        crop,
        cached,
        percent,
        label,
        f"{cached.source} - cached, {age_hours}h old",
        f"Showing the last price Annapurna retrieved, because {reason} Confirm the current rate at your mandi.",
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

        if not settings.agmarknet_api_key and not settings.keyless_market_fallback:
            if cached is not None:
                prices[crop] = cached.modal_price_per_quintal
            continue

        if refreshed >= refresh_limit:
            if cached is not None:
                prices[crop] = cached.modal_price_per_quintal
            continue

        refreshed += 1
        try:
            record, scope = await fetch_from_best_provider(crop, state, district)
        except LiveMarketDataUnavailable as exc:
            if cached is not None:
                prices[crop] = cached.modal_price_per_quintal
            else:
                notes.append(f"{crop}: {exc}")
            continue
        snapshot = await _store(session, crop, scope, record)
        prices[crop] = snapshot.modal_price_per_quintal

    return prices, notes
