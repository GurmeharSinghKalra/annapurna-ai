"""Invariants the ranking must hold for every farm, not just the demo one."""

import itertools

import sqlite3

import pytest

from app.database import get_connection
from app.recommender import CROPS, recommend
from tests.helpers import make_farm, random_farms



# ----- economics ----------------------------------------------------------- #


def test_revenue_is_always_yield_times_price():
    """The old model quoted a revenue that contradicted the price beside it."""
    for farm in random_farms(60):
        for item in recommend(farm):
            assert item.estimated_revenue == item.expected_yield * item.market_price


def test_profit_is_always_revenue_minus_cost():
    for farm in random_farms(60):
        for item in recommend(farm):
            assert item.expected_profit == item.estimated_revenue - item.estimated_cost


def test_margin_matches_the_quoted_revenue_and_profit():
    for farm in random_farms(40):
        for item in recommend(farm):
            if item.estimated_revenue:
                expected = round((item.expected_profit / item.estimated_revenue) * 100)
                assert item.profit_margin == expected


def test_cost_scales_linearly_with_land_size():
    one = {item.crop: item for item in recommend(make_farm(land_size=1))}
    ten = {item.crop: item for item in recommend(make_farm(land_size=10))}
    for crop, item in one.items():
        assert ten[crop].estimated_cost == item.estimated_cost * 10
        assert ten[crop].expected_yield == item.expected_yield * 10


# ----- budget -------------------------------------------------------------- #


def test_budget_shortfall_tracks_land_size():
    """A fixed budget must not stay 'sufficient' as the holding grows."""
    small = next(i for i in recommend(make_farm(land_size=1, budget=30000)) if i.crop == "Sugarcane")
    large = next(i for i in recommend(make_farm(land_size=10, budget=30000)) if i.crop == "Sugarcane")

    assert small.budget_shortfall == small.estimated_cost - 30000
    assert large.budget_shortfall == large.estimated_cost - 30000
    assert large.budget_shortfall > small.budget_shortfall
    assert not large.budget_covers_cost


def test_an_unaffordable_crop_is_ranked_below_its_affordable_self():
    affordable = next(i for i in recommend(make_farm(budget=500_000)) if i.crop == "Sugarcane")
    unaffordable = next(i for i in recommend(make_farm(budget=1000)) if i.crop == "Sugarcane")
    assert unaffordable.suitability < affordable.suitability
    assert any("Budget is short" in caution for caution in unaffordable.cautions)


def test_budget_flags_are_consistent():
    for farm in random_farms(40):
        for item in recommend(farm):
            assert item.budget_covers_cost == (item.budget_shortfall == 0)
            assert item.budget_shortfall >= 0


# ----- scoring ------------------------------------------------------------- #


def test_suitability_stays_within_range():
    for farm in random_farms(80):
        for item in recommend(farm):
            assert 0 <= item.suitability <= 100


def test_scores_are_not_pinned_to_the_ceiling():
    """16% of random farms used to saturate at the old cap, flattening the ranking."""
    tops = [recommend(farm)[0].suitability for farm in random_farms(200)]
    saturated = sum(1 for score in tops if score == 100)
    assert saturated / len(tops) < 0.02
    assert len(set(tops)) > 20, "scores should spread across the range"


def test_ordering_is_deterministic_and_total():
    for farm in random_farms(30):
        first = recommend(farm)
        second = recommend(farm)
        assert [i.crop for i in first] == [i.crop for i in second]
        keys = [(-i.suitability, -i.expected_profit, i.crop) for i in first]
        assert keys == sorted(keys), "results must be sorted by the declared key"


def test_every_crop_is_ranked():
    catalog = {crop["crop"] for crop in CROPS}
    for farm in random_farms(10):
        assert {item.crop for item in recommend(farm)} == catalog


def test_every_recommendation_carries_reasons_or_cautions():
    for farm in random_farms(30):
        for item in recommend(farm):
            assert item.cautions, "cautions must never be empty"
            assert len(item.reasons) <= 4
            assert len(item.cautions) <= 3


# ----- rotation ------------------------------------------------------------ #


def test_repeating_the_previous_crop_is_penalised():
    neutral = next(i for i in recommend(make_farm(season="Rabi", previous_crop="None")) if i.crop == "Wheat")
    repeated = next(i for i in recommend(make_farm(season="Rabi", previous_crop="Wheat")) if i.crop == "Wheat")
    assert repeated.suitability < neutral.suitability
    assert any("Repeating the previous crop" in caution for caution in repeated.cautions)


def test_a_good_rotation_is_rewarded():
    neutral = next(i for i in recommend(make_farm(season="Rabi", previous_crop="None")) if i.crop == "Chickpea")
    rotated = next(i for i in recommend(make_farm(season="Rabi", previous_crop="Wheat")) if i.crop == "Chickpea")
    assert rotated.suitability > neutral.suitability
    assert any("Good rotation after Wheat" in reason for reason in rotated.reasons)


@pytest.mark.parametrize("previous", ["Rice", "Wheat", "Maize", "Chickpea"])
def test_rotation_changes_the_ranking(previous):
    """previous_crop must actually affect output, wherever the advice is rendered."""
    baseline = recommend(make_farm(season="Rabi", previous_crop="None"))
    rotated = recommend(make_farm(season="Rabi", previous_crop=previous))
    assert [i.suitability for i in baseline] != [i.suitability for i in rotated] or [
        i.crop for i in baseline
    ] != [i.crop for i in rotated]


# ----- agronomy ------------------------------------------------------------ #


def test_an_in_range_field_beats_an_out_of_range_one():
    good = next(i for i in recommend(make_farm(season="Kharif", rainfall=200, soil_type="Alluvial")) if i.crop == "Rice")
    bad = next(i for i in recommend(make_farm(season="Kharif", rainfall=0, soil_type="Sandy loam")) if i.crop == "Rice")
    assert good.suitability > bad.suitability


def test_penalties_scale_with_distance_from_the_band():
    near = next(i for i in recommend(make_farm(rainfall=135)) if i.crop == "Rice")
    far = next(i for i in recommend(make_farm(rainfall=0)) if i.crop == "Rice")
    assert near.suitability > far.suitability


def test_sustainability_prefers_low_water_crops():
    ranked = recommend(make_farm(season="Rabi", market_priority="Sustainability"))
    balanced = recommend(make_farm(season="Rabi", market_priority="Balanced"))
    low_water = {"Mustard", "Chickpea"}

    def score(results, crop):
        return next(i.suitability for i in results if i.crop == crop)

    for crop in low_water:
        assert score(ranked, crop) >= score(balanced, crop)


# ----- persistence --------------------------------------------------------- #


def test_connections_are_closed_after_use():
    """`with sqlite3.connect(...)` commits but does not close; the wrapper must."""
    with get_connection() as connection:
        connection.execute("SELECT 1")
    with pytest.raises(sqlite3.ProgrammingError):
        connection.execute("SELECT 1")


def test_connections_are_closed_even_when_the_body_raises():
    captured = {}
    with pytest.raises(ValueError):
        with get_connection() as connection:
            captured["connection"] = connection
            raise ValueError("boom")
    with pytest.raises(sqlite3.ProgrammingError):
        captured["connection"].execute("SELECT 1")


def test_repeated_use_does_not_leak_connections():
    for _ in itertools.repeat(None, 200):
        with get_connection() as connection:
            connection.execute("SELECT 1")
