"""The ranking must be honest: it has to be able to say no, and say why."""

from __future__ import annotations

import pytest

from app.crop_data import CROPS, CROPS_BY_NAME
from app.recommender import recommend, seasonal_water_mm
from app.schemas import FarmProfile


def profile(**overrides) -> FarmProfile:
    base = dict(
        location="Sonipat, Haryana",
        season="Kharif",
        soil_type="Alluvial",
        irrigation="Assured",
        land_size=2,
        ph=6.6,
        nitrogen=62,
        phosphorus=41,
        potassium=48,
        temperature=29,
        humidity=64,
        rainfall=600,
        budget=120_000,
    )
    base.update(overrides)
    return FarmProfile(**base)


def test_a_hopeless_field_is_told_so():
    """The old scorer clamped suitability to a floor of 36, so nothing was ever unsuitable."""
    ranked = recommend(
        profile(
            soil_type="Sandy loam",
            irrigation="Rainfed",
            ph=10,
            nitrogen=0,
            phosphorus=0,
            potassium=0,
            temperature=50,
            rainfall=0,
            budget=0,
        )
    )
    assert all(item.suitability < 40 for item in ranked), [(i.crop, i.suitability) for i in ranked]
    assert all(item.verdict in {"marginal", "not recommended"} for item in ranked)
    assert all(item.limiters for item in ranked), "every crop must name what rules it out"


def test_out_of_season_crops_cannot_rank_well():
    ranked = {item.crop: item for item in recommend(profile(season="Kharif"))}
    for rabi_crop in ("Wheat", "Mustard", "Chickpea"):
        item = ranked[rabi_crop]
        assert item.suitability <= 30
        assert any("cannot be sown" in reason for reason in item.limiters)


def test_annual_crops_do_not_get_a_free_season_match():
    """Sugarcane used to take the full season bonus in every season, so it ranked first in Rabi."""
    ranked = recommend(profile(season="Rabi", temperature=18, rainfall=150))
    sugarcane = next(item for item in ranked if item.crop == "Sugarcane")
    wheat = next(item for item in ranked if item.crop == "Wheat")
    assert wheat.suitability > sugarcane.suitability
    assert any("occupies the field" in caution for caution in sugarcane.cautions)


def test_rainfed_fields_are_not_offered_thirsty_crops():
    assured = {item.crop: item.suitability for item in recommend(profile(irrigation="Assured"))}
    rainfed = {item.crop: item.suitability for item in recommend(profile(irrigation="Rainfed", rainfall=350))}
    assert assured["Rice"] > 70
    assert rainfed["Rice"] <= 30
    rice = next(item for item in recommend(profile(irrigation="Rainfed", rainfall=350)) if item.crop == "Rice")
    assert any("rainfed" in text.lower() or "short by" in text for text in rice.limiters)


def test_irrigation_changes_the_water_budget():
    assert seasonal_water_mm(profile(rainfall=400, irrigation="Rainfed")) == 400
    assert seasonal_water_mm(profile(rainfall=400, irrigation="Limited")) == 650
    assert seasonal_water_mm(profile(rainfall=400, irrigation="Assured")) == 1300


def test_soil_mismatch_is_a_limiter_not_a_small_deduction():
    cotton = next(item for item in recommend(profile(soil_type="Alluvial")) if item.crop == "Cotton")
    assert cotton.suitability <= 62
    assert any("soil" in text for text in cotton.limiters)


def test_sustainability_responds_to_the_field_not_just_the_crop():
    """It used to be a per-crop constant, identical for every farm and every priority."""
    wet = {item.crop: item.sustainability_score for item in recommend(profile(rainfall=1200))}
    dry = {item.crop: item.sustainability_score for item in recommend(profile(rainfall=100))}
    assert dry["Rice"] < wet["Rice"], "a thirsty crop on a dry field must score worse"
    assert all(0 <= score <= 100 for score in list(wet.values()) + list(dry.values()))


def test_repeating_last_season_crop_is_penalised_and_explained():
    ranked = {item.crop: item for item in recommend(profile(season="Kharif", previous_crop="Rice"))}
    assert any("repeating" in caution.lower() for caution in ranked["Rice"].cautions)


def test_economics_are_ranges_and_internally_consistent():
    for item in recommend(profile()):
        economics = item.economics
        assert (
            economics.expected_yield_quintal.low
            <= economics.expected_yield_quintal.typical
            <= economics.expected_yield_quintal.high
        )
        assert (
            economics.estimated_cost_inr.low
            <= economics.estimated_cost_inr.typical
            <= economics.estimated_cost_inr.high
        )
        assert (
            economics.expected_profit_inr.low
            <= economics.expected_profit_inr.typical
            <= economics.expected_profit_inr.high
        )
        # The headline figures must be the typical case, not a different calculation.
        assert item.expected_profit == economics.expected_profit_inr.typical
        assert item.estimated_cost == economics.estimated_cost_inr.typical
        assert item.estimated_revenue == economics.estimated_revenue_inr.typical


def test_revenue_equals_yield_times_the_stated_price():
    for item in recommend(profile()):
        expected = round(item.economics.expected_yield_quintal.typical * item.market_price)
        assert abs(item.estimated_revenue - expected) <= 1


def test_a_live_price_overrides_the_reference_price_and_is_labelled():
    without = next(i for i in recommend(profile()) if i.crop == "Rice")
    withlive = next(i for i in recommend(profile(), prices={"Rice": 3000}) if i.crop == "Rice")
    assert "MSP" in without.price_basis
    assert withlive.market_price == 3000
    assert withlive.price_basis == "live mandi modal price"
    assert withlive.estimated_revenue > without.estimated_revenue


def test_economics_scale_linearly_with_land_size():
    one = next(i for i in recommend(profile(land_size=1)) if i.crop == "Maize")
    ten = next(i for i in recommend(profile(land_size=10)) if i.crop == "Maize")
    assert ten.estimated_cost == pytest.approx(one.estimated_cost * 10, rel=0.01)


def test_every_crop_carries_its_sources_and_a_price_basis():
    for crop in CROPS:
        assert crop.sources, f"{crop.name} has no cited source"
        assert crop.reference_price_basis
        assert crop.yield_quintal_per_acre.low > 0
        assert crop.cost_inr_per_acre.low > 0


def test_cotton_economics_are_not_the_old_fantasy():
    """The table claimed 16 q/acre, implying a ~75,000/acre profit no Haryana study supports."""
    cotton = CROPS_BY_NAME["Cotton"]
    assert cotton.yield_quintal_per_acre.high <= 12
    assert cotton.yield_quintal_per_acre.typical <= 8
    # A poor cotton season must be able to show a loss, because in this region it frequently is one.
    poor = next(i for i in recommend(profile(soil_type="Black")) if i.crop == "Cotton")
    assert poor.economics.expected_profit_inr.low < 0


def test_ranking_is_deterministic():
    first = [(i.crop, i.suitability) for i in recommend(profile())]
    second = [(i.crop, i.suitability) for i in recommend(profile())]
    assert first == second


@pytest.mark.parametrize("season", ["Kharif", "Rabi", "Annual"])
@pytest.mark.parametrize("irrigation", ["Rainfed", "Limited", "Assured"])
def test_no_combination_crashes_or_escapes_its_bounds(season, irrigation):
    for item in recommend(profile(season=season, irrigation=irrigation)):
        assert 0 <= item.suitability <= 100
        assert 0 <= item.sustainability_score <= 100
        assert item.verdict
        assert item.cautions, "a crop must always say something about its risk"


# --------------------------------------------------------------------- the optional model


def test_an_unevaluated_model_is_refused(monkeypatch, tmp_path):
    """Any .joblib on disk used to influence every recommendation with nothing measuring it."""
    from app import ml_model

    monkeypatch.setattr(ml_model, "MODEL_PATH", tmp_path / "model.joblib")
    monkeypatch.setattr(ml_model, "METRICS_PATH", tmp_path / "missing.json")
    (tmp_path / "model.joblib").write_bytes(b"not really a model")
    ml_model.reset_cache()
    try:
        assert ml_model.model_available() is False
        assert ml_model.model_report()["status"] == "not_in_use"
    finally:
        ml_model.reset_cache()


def test_a_model_that_cannot_beat_its_baseline_is_refused(monkeypatch, tmp_path):
    import json

    from app import ml_model

    (tmp_path / "model.joblib").write_bytes(b"x")
    (tmp_path / "metrics.json").write_text(json.dumps({"holdout_accuracy": 0.2, "baseline_accuracy": 0.3}))
    monkeypatch.setattr(ml_model, "MODEL_PATH", tmp_path / "model.joblib")
    monkeypatch.setattr(ml_model, "METRICS_PATH", tmp_path / "metrics.json")
    ml_model.reset_cache()
    try:
        assert ml_model.model_available() is False
    finally:
        ml_model.reset_cache()


def test_influence_is_scaled_by_the_independent_score():
    from app.ml_model import _trust_from

    # Strong on its own training distribution but weak against unseen data: little influence.
    assert (
        _trust_from({"holdout_accuracy": 0.95, "baseline_accuracy": 0.12, "observational_sample_accuracy": 0.3}) == 0.3
    )
    # Strong on both: full influence.
    assert (
        _trust_from({"holdout_accuracy": 0.95, "baseline_accuracy": 0.12, "observational_sample_accuracy": 0.9}) == 0.9
    )
    # No independent check at all: capped.
    assert _trust_from({"holdout_accuracy": 0.99, "baseline_accuracy": 0.12}) <= 0.4
    # Worse than guessing: none.
    assert _trust_from({"holdout_accuracy": 0.1, "baseline_accuracy": 0.3}) == 0.0


def test_a_corrupt_model_falls_back_to_rules_without_crashing(monkeypatch):
    from app import ml_model

    monkeypatch.setattr(ml_model.joblib, "load", lambda path: (_ for _ in ()).throw(ValueError("corrupt model")))
    ml_model.reset_cache()
    try:
        assert ml_model.model_available() is False
        assert ml_model.predict_crop(profile()) == (None, 0.0)
        # The ranking must still work.
        assert recommend(profile())
    finally:
        ml_model.reset_cache()


def test_the_model_cannot_override_a_hard_limiter(monkeypatch):
    """Even if the model votes for it, an out-of-season crop must stay out of season."""
    from app import ml_model

    monkeypatch.setattr(ml_model, "predict_crop", lambda farm: ("Wheat", 1.0))
    from app import recommender

    monkeypatch.setattr(recommender, "predict_crop", lambda farm: ("Wheat", 1.0))
    wheat = next(item for item in recommend(profile(season="Kharif")) if item.crop == "Wheat")
    assert wheat.suitability <= 30
    assert wheat.verdict == "not recommended"
