"""Season profitability planning built on the crop recommendation.

This is a planning tool. It does not offer loans, assess credit, or touch bank accounts.

Changes from the first version:

* **Scenarios come from the crop's real yield and cost ranges**, not from multiplying everything by
  an arbitrary 0.85. A bad cotton year and a bad wheat year are not the same size of shock, and
  pretending they are understates the risk on exactly the crops where it matters most.
* **Break-even uses the unrounded yield.** Rounding the yield first made break-even price jump
  around on small plots: 0.1 acre and 0.2 acre of mustard both reported 2,200/quintal while
  0.5 acre reported 1,833.
* **Peak working capital is reported**, because the number that decides whether a farmer can
  actually fund a season is the largest cumulative outflow before any money comes in, not the
  season total.
* **Unknown expense categories are rejected** rather than silently discarded.
"""

from __future__ import annotations

from .crop_data import CROPS_BY_NAME
from .recommender import recommend
from .schemas import FinancialPlanRequest

# Share of total cultivation cost by category, and when in the season it is spent. Shares sum to 1.
EXPENSE_PLAN: dict[str, dict[str, float]] = {
    "Seeds and planting": {"share": 0.18, "before_sowing": 1.00, "growing": 0.00, "harvest": 0.00},
    "Fertilizer and soil inputs": {"share": 0.22, "before_sowing": 0.40, "growing": 0.60, "harvest": 0.00},
    "Crop protection": {"share": 0.12, "before_sowing": 0.00, "growing": 1.00, "harvest": 0.00},
    "Irrigation and power": {"share": 0.10, "before_sowing": 0.10, "growing": 0.90, "harvest": 0.00},
    "Labour": {"share": 0.20, "before_sowing": 0.25, "growing": 0.35, "harvest": 0.40},
    "Machinery": {"share": 0.10, "before_sowing": 0.45, "growing": 0.10, "harvest": 0.45},
    "Transport and market": {"share": 0.08, "before_sowing": 0.00, "growing": 0.00, "harvest": 1.00},
}

EXPENSE_CATEGORIES = tuple(EXPENSE_PLAN)

STAGES = (
    ("Before sowing", "before_sowing"),
    ("Growing period", "growing"),
    ("Harvest and transport", "harvest"),
)


class UnknownExpenseCategory(ValueError):
    """The caller sent an expense category the planner does not budget for."""


def _round(value: float) -> int:
    return max(0, round(value))


def season_financial_plan(request: FinancialPlanRequest, prices: dict[str, int] | None = None) -> dict:
    """Build a season budget for the selected crop.

    ``prices`` optionally supplies live mandi prices, in the same shape ``recommend`` accepts.
    """
    unknown = set(request.actual_expenses) - set(EXPENSE_CATEGORIES)
    if unknown:
        raise UnknownExpenseCategory(
            f"Unknown expense {'categories' if len(unknown) > 1 else 'category'}: "
            f"{', '.join(sorted(unknown))}. Valid categories: {', '.join(EXPENSE_CATEGORIES)}"
        )

    recommendations = recommend(request.farm, prices)
    selected = next((item for item in recommendations if item.crop == request.crop), None)
    if request.crop and selected is None:
        raise ValueError(
            f"'{request.crop}' is not a crop this planner covers. Choose one of: {', '.join(sorted(CROPS_BY_NAME))}"
        )
    selected = selected or recommendations[0]

    case = request.yield_case
    planned_total = float(getattr(selected.economics.estimated_cost_inr, case))
    expected_yield = float(getattr(selected.economics.expected_yield_quintal, case))

    expenses = []
    for category, plan in EXPENSE_PLAN.items():
        planned = _round(planned_total * plan["share"])
        actual = _round(request.actual_expenses.get(category, planned))
        expenses.append({"category": category, "planned": planned, "actual": actual, "variance": actual - planned})

    planned_cost = sum(item["planned"] for item in expenses)
    actual_cost = sum(item["actual"] for item in expenses)

    if request.market_price_per_quintal is not None:
        price = request.market_price_per_quintal
        planning_source = "farmer-entered local mandi price"
        price_note = "You supplied this price. Check it is for the right crop, unit, mandi and date."
    elif selected.crop in request.farm.known_market_prices:
        price = request.farm.known_market_prices[selected.crop]
        planning_source = "the price you entered for your own mandi"
        price_note = "You supplied this price. Check it is for the right crop, unit, mandi and date."
    else:
        price = selected.market_price
        planning_source = selected.price_basis
        price_note = (
            "A live mandi modal price."
            if selected.price_basis == "live mandi modal price"
            else f"An announced support price ({selected.price_basis}), not a guaranteed sale price."
        )

    expected_revenue = _round(expected_yield * price)
    expected_profit = expected_revenue - actual_cost
    # Unrounded yield: rounding first makes break-even non-monotonic on small plots.
    break_even_price = round(actual_cost / expected_yield) if expected_yield > 0 else 0
    budget_gap = max(0, actual_cost - _round(request.farm.budget))

    cash_flow = []
    cumulative = 0
    peak_outflow = 0
    for label, key in STAGES:
        cash_out = _round(sum(item["actual"] * EXPENSE_PLAN[item["category"]][key] for item in expenses))
        cumulative += cash_out
        peak_outflow = max(peak_outflow, cumulative)
        cash_flow.append({"stage": label, "cash_out": cash_out, "cash_in": 0, "cumulative_cash_out": cumulative})
    # Rounding each stage can drift from the total by a rupee or two; put the difference where the
    # money is actually settled rather than leaving the stages inconsistent with the total.
    drift = actual_cost - cumulative
    if drift:
        cash_flow[-1]["cash_out"] += drift
        cash_flow[-1]["cumulative_cash_out"] += drift
        peak_outflow = max(peak_outflow, cash_flow[-1]["cumulative_cash_out"])
    cash_flow.append(
        {"stage": "Expected sale", "cash_out": 0, "cash_in": expected_revenue, "cumulative_cash_out": actual_cost}
    )

    economics = selected.economics
    scenarios = [
        {
            "name": "Good season",
            "basis": "high yield against low cost",
            "yield_quintal": economics.expected_yield_quintal.high,
            "price_per_quintal": price,
            "revenue": _round(economics.expected_yield_quintal.high * price),
            "cost": _round(economics.estimated_cost_inr.low),
        },
        {
            "name": "Typical season",
            "basis": "typical yield and cost at the planning price",
            "yield_quintal": economics.expected_yield_quintal.typical,
            "price_per_quintal": price,
            "revenue": _round(economics.expected_yield_quintal.typical * price),
            "cost": actual_cost,
        },
        {
            "name": "Price falls 15%",
            "basis": "typical yield, price 15% below the planning price",
            "yield_quintal": economics.expected_yield_quintal.typical,
            "price_per_quintal": round(price * 0.85),
            "revenue": _round(economics.expected_yield_quintal.typical * price * 0.85),
            "cost": actual_cost,
        },
        {
            "name": "Poor season",
            "basis": "low yield against high cost at the planning price",
            "yield_quintal": economics.expected_yield_quintal.low,
            "price_per_quintal": price,
            "revenue": _round(economics.expected_yield_quintal.low * price),
            "cost": _round(economics.estimated_cost_inr.high),
        },
    ]
    for scenario in scenarios:
        scenario["profit"] = scenario["revenue"] - scenario["cost"]
        scenario["margin"] = round((scenario["profit"] / scenario["revenue"]) * 100) if scenario["revenue"] else 0

    worst = min(scenarios, key=lambda item: item["profit"])

    return {
        "crop": selected.crop,
        "planning_source": planning_source,
        "price_note": price_note,
        "yield_case": case,
        "currency": "INR",
        "expenses": expenses,
        "cash_flow": cash_flow,
        "scenarios": scenarios,
        "summary": {
            "planned_cost": planned_cost,
            "actual_cost": actual_cost,
            "expected_revenue": expected_revenue,
            "expected_profit": expected_profit,
            "profit_margin": round((expected_profit / expected_revenue) * 100) if expected_revenue else 0,
            "working_capital_gap": budget_gap,
            "peak_working_capital": peak_outflow,
            "budget_remaining": max(0, _round(request.farm.budget) - actual_cost),
            "break_even_price_per_quintal": break_even_price,
            "break_even_yield_quintal": round(actual_cost / price, 1) if price else 0,
            "expected_yield_quintal": round(expected_yield, 1),
            "planning_market_price_per_quintal": price,
            "worst_case_profit": worst["profit"],
            "worst_case_name": worst["name"],
        },
        "disclaimer": (
            "Planning estimates only. Not a loan, credit, or investment recommendation, and not a "
            "guarantee of yield, price, or income."
        ),
    }
