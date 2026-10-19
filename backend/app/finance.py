"""Season profitability planning built from Annapurna's crop recommendation output.

This module is deliberately a planning tool. It does not offer loans, assess credit,
or connect to bank accounts. All numbers are estimates until the farmer replaces
the planning values with actual expenses and official market data is connected.
"""

from .integrations import fetch_market_profile
from .recommender import recommend
from .schemas import FinancialPlanRequest


EXPENSE_WEIGHTS = {
    "Seeds and planting": 0.18,
    "Fertilizer and soil inputs": 0.22,
    "Crop protection": 0.12,
    "Irrigation and power": 0.10,
    "Labour": 0.20,
    "Machinery": 0.10,
    "Transport and market": 0.08,
}


def _round_amount(value: float) -> int:
    return max(0, round(value))


async def season_financial_plan(request: FinancialPlanRequest) -> dict:
    recommendations = recommend(request.farm)
    selected = next((item for item in recommendations if item.crop == request.crop), None)
    if request.crop and selected is None:
        raise ValueError("Select a crop returned by the current recommendation plan")
    selected = selected or recommendations[0]
    planned_expenses = [
        {"category": category, "planned": _round_amount(selected.estimated_cost * weight)}
        for category, weight in EXPENSE_WEIGHTS.items()
    ]
    expenses = []
    for item in planned_expenses:
        actual = request.actual_expenses.get(item["category"], item["planned"])
        actual = _round_amount(actual)
        expenses.append({
            **item,
            "actual": actual,
            "variance": actual - item["planned"],
        })

    planned_cost = sum(item["planned"] for item in expenses)
    actual_cost = sum(item["actual"] for item in expenses)
    expected_yield = selected.expected_yield
    if request.market_price_per_quintal is not None:
        market = {
            "source": "farmer-entered local mandi price",
            "modal_price_per_quintal": request.market_price_per_quintal,
            "note": "Manual market price supplied for this plan. Verify its mandi, unit, and date before acting.",
        }
    else:
        market = await fetch_market_profile(request.farm, selected.crop, selected.expected_profit)
    planning_market_price = market["modal_price_per_quintal"]
    # The finance screen must use one coherent revenue assumption: its displayed
    # per-quintal planning price multiplied by its displayed expected yield.
    expected_revenue = _round_amount(expected_yield * planning_market_price)
    expected_profit = expected_revenue - actual_cost
    break_even_price = round(actual_cost / expected_yield) if expected_yield else 0
    budget_gap = max(0, actual_cost - request.farm.budget)

    scenarios = [
        {"name": "Base plan", "yield_factor": 1, "price_factor": 1},
        {"name": "Lower market price", "yield_factor": 1, "price_factor": 0.85},
        {"name": "Lower yield", "yield_factor": 0.85, "price_factor": 1},
        {"name": "Combined risk", "yield_factor": 0.85, "price_factor": 0.85},
    ]
    for scenario in scenarios:
        revenue = _round_amount(expected_revenue * scenario["yield_factor"] * scenario["price_factor"])
        scenario["revenue"] = revenue
        scenario["profit"] = revenue - actual_cost
        scenario["margin"] = round((scenario["profit"] / revenue) * 100) if revenue else 0
        scenario.pop("yield_factor")
        scenario.pop("price_factor")

    cash_flow = [
        {"stage": "Before sowing", "share": 30, "cash_out": _round_amount(actual_cost * 0.30), "cash_in": 0},
        {"stage": "Growing period", "share": 40, "cash_out": _round_amount(actual_cost * 0.40), "cash_in": 0},
        {"stage": "Harvest and transport", "share": 30, "cash_out": actual_cost - _round_amount(actual_cost * 0.70), "cash_in": 0},
        {"stage": "Expected sale", "share": 0, "cash_out": 0, "cash_in": expected_revenue},
    ]

    return {
        "crop": selected.crop,
        "planning_source": market["source"],
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
            "budget_remaining": max(0, _round_amount(request.farm.budget) - actual_cost),
            "break_even_price_per_quintal": break_even_price,
            "expected_yield_quintal": expected_yield,
            "planning_market_price_per_quintal": planning_market_price,
        },
    }
