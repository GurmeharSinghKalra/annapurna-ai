from .recommender import recommend
from .schemas import FarmProfile


def recommendation_report(farm: FarmProfile) -> str:
    top = recommend(farm)[0]
    lines = [
        "Annapurna AI Crop Recommendation Report",
        "",
        f"Farmer: {farm.farmer_name}",
        f"Phone: {farm.phone}",
        f"Location: {farm.location}",
        f"Language: {farm.language}",
        f"Season: {farm.season}",
        f"Previous crop: {farm.previous_crop}",
        f"Soil type: {farm.soil_type}",
        f"Land size: {farm.land_size} acre",
        f"Budget: INR {farm.budget:,.0f}",
        "",
        f"Recommended crop: {top.crop}",
        f"Suitability: {top.suitability}%",
        f"Expected yield: {top.expected_yield} quintal",
        f"Expected return: INR {top.expected_profit:,}",
        f"Estimated cultivation cost: INR {top.estimated_cost:,}",
        f"Estimated revenue: INR {top.estimated_revenue:,}",
        f"Estimated profit margin: {top.profit_margin}%",
        f"Market planning price: INR {top.market_price:,}/quintal ({top.market_trend:+.1f}% trend)",
        f"Sustainability score: {top.sustainability_score}/100",
        f"Water need: {top.water}",
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
    ]
    return "\n".join(lines)
