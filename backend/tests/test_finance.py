"""Season budgeting: the arithmetic a farmer would be harmed by getting wrong."""

from __future__ import annotations

import pytest

from app.finance import EXPENSE_CATEGORIES, UnknownExpenseCategory, season_financial_plan
from app.schemas import FarmProfile, FinancialPlanRequest


def request_for(crop="Maize", **farm_overrides) -> FinancialPlanRequest:
    base = dict(
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
    base.update(farm_overrides)
    return FinancialPlanRequest(farm=FarmProfile(**base), crop=crop)


@pytest.mark.parametrize("land_size", [0.1, 0.2, 0.3, 0.5, 1, 2, 5, 20])
def test_break_even_price_is_stable_across_plot_sizes(land_size):
    """Rounding the yield before the division made this jump: 2200, 2200, then 1833/quintal."""
    plans = [season_financial_plan(request_for(land_size=size)) for size in (0.1, 0.5, 2, 20)]
    values = {plan["summary"]["break_even_price_per_quintal"] for plan in plans}
    assert len(values) == 1, f"break-even moved with plot size: {values}"


def test_cash_flow_stages_sum_to_the_total_cost():
    plan = season_financial_plan(request_for())
    assert sum(stage["cash_out"] for stage in plan["cash_flow"]) == plan["summary"]["actual_cost"]


def test_cash_flow_is_cumulative_and_reports_the_true_peak():
    plan = season_financial_plan(request_for())
    running = 0
    for stage in plan["cash_flow"][:-1]:
        running += stage["cash_out"]
        assert stage["cumulative_cash_out"] == running
    # The number that decides whether a season can be funded is the largest outflow before
    # any money arrives, not the season total.
    assert plan["summary"]["peak_working_capital"] == running


def test_scenarios_use_the_crops_real_ranges_not_a_flat_multiplier():
    plan = season_financial_plan(request_for("Cotton", soil_type="Black"))
    names = [scenario["name"] for scenario in plan["scenarios"]]
    assert names == ["Good season", "Typical season", "Price falls 15%", "Poor season"]
    good = next(s for s in plan["scenarios"] if s["name"] == "Good season")
    poor = next(s for s in plan["scenarios"] if s["name"] == "Poor season")
    assert poor["yield_quintal"] < good["yield_quintal"]
    assert poor["cost"] > good["cost"], "a poor season costs more, not less"
    assert poor["profit"] < good["profit"]
    assert plan["summary"]["worst_case_profit"] == min(s["profit"] for s in plan["scenarios"])


def test_unknown_expense_categories_are_rejected_not_silently_dropped():
    bad = request_for().model_copy(update={"actual_expenses": {"Bribes": 500}})
    with pytest.raises(UnknownExpenseCategory) as caught:
        season_financial_plan(bad)
    assert "Bribes" in str(caught.value)


def test_known_expense_categories_replace_the_plan():
    tracked = request_for().model_copy(update={"actual_expenses": {"Labour": 30_000}})
    plan = season_financial_plan(tracked)
    labour = next(item for item in plan["expenses"] if item["category"] == "Labour")
    assert labour["actual"] == 30_000
    assert labour["variance"] == 30_000 - labour["planned"]
    assert plan["summary"]["actual_cost"] == sum(item["actual"] for item in plan["expenses"])


def test_expense_shares_cover_the_whole_cost():
    plan = season_financial_plan(request_for())
    assert {item["category"] for item in plan["expenses"]} == set(EXPENSE_CATEGORIES)
    assert abs(plan["summary"]["planned_cost"] - plan["summary"]["actual_cost"]) <= 1


def test_a_farmer_supplied_price_overrides_the_reference_and_is_labelled():
    plan = season_financial_plan(request_for().model_copy(update={"market_price_per_quintal": 2600}))
    assert plan["planning_source"] == "farmer-entered local mandi price"
    assert plan["summary"]["planning_market_price_per_quintal"] == 2600
    assert plan["summary"]["expected_revenue"] == round(plan["summary"]["expected_yield_quintal"] * 2600)


def test_budgeting_against_a_low_yield_is_more_conservative():
    low = season_financial_plan(request_for().model_copy(update={"yield_case": "low"}))
    typical = season_financial_plan(request_for())
    assert low["summary"]["expected_yield_quintal"] < typical["summary"]["expected_yield_quintal"]
    assert low["summary"]["expected_profit"] < typical["summary"]["expected_profit"]
    # Costs fall too, so break-even per quintal must still be a sane positive number.
    assert low["summary"]["break_even_price_per_quintal"] > 0


def test_a_crop_outside_the_catalogue_is_refused_with_the_valid_list():
    with pytest.raises(ValueError) as caught:
        season_financial_plan(request_for("Unobtainium"))
    assert "Unobtainium" in str(caught.value)
    assert "Maize" in str(caught.value)


def test_working_capital_gap_appears_only_when_the_budget_is_short():
    rich = season_financial_plan(request_for(budget=10_000_000))
    assert rich["summary"]["working_capital_gap"] == 0
    poor = season_financial_plan(request_for(budget=0))
    assert poor["summary"]["working_capital_gap"] == poor["summary"]["actual_cost"]
    assert poor["summary"]["budget_remaining"] == 0


def test_margin_and_break_even_never_divide_by_zero():
    plan = season_financial_plan(request_for().model_copy(update={"market_price_per_quintal": 1}))
    assert isinstance(plan["summary"]["profit_margin"], int)
    assert plan["summary"]["break_even_price_per_quintal"] >= 0


def test_plan_carries_its_disclaimer_and_price_basis():
    plan = season_financial_plan(request_for())
    assert "not a loan" in plan["disclaimer"].lower()
    assert plan["price_note"]
