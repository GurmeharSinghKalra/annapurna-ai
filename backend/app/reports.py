from .recommender import recommend
from .schemas import FarmProfile


def recommendation_report(farm: FarmProfile) -> str:
    top = recommend(farm)[0]

    identity = []
    if farm.farmer_name:
        identity.append(f"Farmer: {farm.farmer_name}")
    if farm.phone:
        identity.append(f"Phone: {farm.phone}")

    budget_line = (
        f"Budget: INR {farm.budget:,.0f} (covers estimated cost)"
        if top.budget_covers_cost
        else f"Budget: INR {farm.budget:,.0f} (short by INR {top.budget_shortfall:,} of estimated cost)"
    )

    lines = [
        "Annapurna AI Crop Recommendation Report",
        "",
        *identity,
        f"Location: {farm.location}",
        f"Language: {farm.language}",
        f"Season: {farm.season}",
        f"Previous crop: {farm.previous_crop}",
        f"Soil type: {farm.soil_type}",
        f"Land size: {farm.land_size} acre",
        budget_line,
        "",
        f"Recommended crop: {top.crop}",
        f"Suitability: {top.suitability}%",
        "",
        "Economics (revenue = expected yield x planning price):",
        f"- Expected yield: {top.expected_yield} quintal",
        f"- Market planning price: INR {top.market_price:,}/quintal ({top.market_trend:+.1f}% trend)",
        f"- Estimated revenue: INR {top.estimated_revenue:,}",
        f"- Estimated cultivation cost: INR {top.estimated_cost:,}",
        f"- Expected net return: INR {top.expected_profit:,}",
        f"- Profit margin: {top.profit_margin}%",
        "",
        f"Sustainability score: {top.sustainability_score}/100",
        f"Water need: {top.water}",
        f"Model influence: {top.ml_influence}",
        "",
        "Reasons:",
        *[f"- {reason}" for reason in top.reasons],
        "",
        "Warnings:",
        *[f"- {warning}" for warning in top.cautions],
        "",
        "Advisory:",
        top.advisory,
        top.rotation,
        top.sustainability,
        "",
        "These are planning estimates, not guaranteed outcomes. Verify prices and",
        "treatment decisions with local expertise before investing.",
    ]
    return "\n".join(lines)
