from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .recommender import recommend
from .schemas import FarmProfile, PdfReportRequest


FOREST = colors.HexColor("#173f36")
LEAF = colors.HexColor("#4f765c")
SAFFRON = colors.HexColor("#d58b2b")
PAPER = colors.HexColor("#fbfaf4")
INK = colors.HexColor("#1d2a28")
MUTED = colors.HexColor("#64716c")


def _inr(value: Any) -> str:
    try:
        return f"INR {round(float(value)):,}"
    except (TypeError, ValueError):
        return "Not available"


def _value(source: dict[str, Any] | None, key: str, default: str = "Not available") -> str:
    if not source or source.get(key) in (None, ""):
        return default
    return str(source[key])


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#d9dfd7"))
    canvas.line(18 * mm, 14 * mm, 192 * mm, 14 * mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 9 * mm, "Annapurna AI - profile-specific decision support")
    canvas.drawRightString(192 * mm, 9 * mm, f"Page {doc.page}")
    canvas.restoreState()


def pdf_report(request: PdfReportRequest) -> bytes:
    """Create a compact, printable farm and finance report from the current app snapshot."""
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=20 * mm,
        title="Annapurna AI Farm Report",
        author="Annapurna AI",
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle("ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=25, leading=30, textColor=FOREST, spaceAfter=3)
    subtitle = ParagraphStyle("ReportSubtitle", parent=styles["Normal"], fontSize=9, leading=13, textColor=MUTED, spaceAfter=14)
    heading = ParagraphStyle("ReportHeading", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=13, leading=18, textColor=FOREST, spaceBefore=10, spaceAfter=7)
    body = ParagraphStyle("ReportBody", parent=styles["BodyText"], fontSize=9, leading=14, textColor=INK)
    caption = ParagraphStyle("ReportCaption", parent=body, fontSize=8, leading=11, textColor=MUTED)

    farm = request.farm
    recommendation = request.recommendation
    story = [
        Paragraph("ANNAPURNA AI", ParagraphStyle("Brand", parent=body, fontName="Helvetica-Bold", fontSize=8, textColor=SAFFRON, alignment=TA_CENTER, letterSpacing=1.5)),
        Paragraph("Farm Decision & Season Finance Report", title),
        Paragraph("Prepared from the farmer profile and the latest analysis snapshot. Values marked as estimates must be verified locally before acting.", subtitle),
    ]
    profile_rows = [
        ["Farmer", farm.farmer_name, "Location", farm.location],
        ["Season", farm.season, "Land size", f"{farm.land_size:g} acre"],
        ["Soil", farm.soil_type, "Planning budget", _inr(farm.budget)],
    ]
    profile_table = Table(profile_rows, colWidths=[28 * mm, 57 * mm, 32 * mm, 57 * mm])
    profile_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PAPER), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d9dfd7")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (0, -1), FOREST), ("TEXTCOLOR", (2, 0), (2, -1), FOREST),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story += [Paragraph("Farm profile", heading), profile_table, Paragraph("Crop recommendation", heading)]

    metrics = [["Recommended crop", recommendation.crop, "Suitability", f"{recommendation.suitability}%"], ["Expected yield", f"{recommendation.expected_yield} quintal", "Water need", recommendation.water], ["Estimated cost", _inr(recommendation.estimated_cost), "Estimated revenue", _inr(recommendation.estimated_revenue)], ["Estimated profit", _inr(recommendation.expected_profit), "Profit margin", f"{recommendation.profit_margin}%"]]
    metrics_table = Table(metrics, colWidths=[35 * mm, 50 * mm, 35 * mm, 54 * mm])
    metrics_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9f0e8")), ("BACKGROUND", (0, 1), (-1, -1), PAPER),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d9dfd7")), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"), ("TEXTCOLOR", (0, 0), (0, -1), FOREST), ("TEXTCOLOR", (2, 0), (2, -1), FOREST),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story += [metrics_table, Spacer(1, 7), Paragraph(f"<b>Why this crop:</b> {', '.join(recommendation.reasons)}", body), Paragraph(f"<b>Watch:</b> {', '.join(recommendation.cautions) or 'No additional caution returned.'}", body)]

    story.append(Paragraph("Live data context", heading))
    weather = request.weather or {}
    market = request.market or {}
    live_rows = [["Weather source", _value(weather, "source"), "Market source", _value(market, "source")], ["Temperature", f"{_value(weather, 'temperature')} C", "Modal price", f"{_inr(market.get('modal_price_per_quintal'))}/quintal"], ["Weather alert", _value(weather, "alert"), "Mandi / date", f"{_value(market, 'market')} / {_value(market, 'observed_at')}"]]
    live_table = Table(live_rows, colWidths=[35 * mm, 50 * mm, 35 * mm, 54 * mm])
    live_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PAPER), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d9dfd7")), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"), ("TEXTCOLOR", (0, 0), (0, -1), FOREST), ("TEXTCOLOR", (2, 0), (2, -1), FOREST), ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    story.append(live_table)

    finance = request.finance or {}
    if finance:
        summary = finance.get("summary") or {}
        story.append(Paragraph("Season finance", heading))
        finance_rows = [["Working capital", _inr(summary.get("actual_cost")), "Expected revenue", _inr(summary.get("expected_revenue"))], ["Expected profit", _inr(summary.get("expected_profit")), "Break-even price", f"{_inr(summary.get('break_even_price_per_quintal'))}/quintal"], ["Profit margin", f"{_value(summary, 'profit_margin')}%", "Planning source", _value(finance, "planning_source")]]
        finance_table = Table(finance_rows, colWidths=[35 * mm, 50 * mm, 35 * mm, 54 * mm])
        finance_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fff1dc")), ("BACKGROUND", (0, 1), (-1, -1), PAPER), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d9dfd7")), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"), ("TEXTCOLOR", (0, 0), (0, -1), FOREST), ("TEXTCOLOR", (2, 0), (2, -1), FOREST), ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
        story.append(finance_table)
        expenses = finance.get("expenses") or []
        if expenses:
            story.append(Spacer(1, 8))
            expense_rows = [["Expense category", "Planned", "Tracked", "Variance"]] + [[_value(item, "category"), _inr(item.get("planned")), _inr(item.get("actual")), _inr(item.get("variance"))] for item in expenses]
            expense_table = Table(expense_rows, colWidths=[70 * mm, 34 * mm, 34 * mm, 36 * mm], repeatRows=1)
            expense_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), FOREST), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("BACKGROUND", (0, 1), (-1, -1), PAPER), ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d9dfd7")), ("FONTSIZE", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("ALIGN", (1, 1), (-1, -1), "RIGHT")]))
            story += [Paragraph("Expense tracker", heading), expense_table]
        scenarios = finance.get("scenarios") or []
        if scenarios:
            story.append(Paragraph("Risk scenarios", heading))
            scenario_rows = [["Scenario", "Revenue", "Profit", "Margin"]] + [[_value(item, "name"), _inr(item.get("revenue")), _inr(item.get("profit")), f"{_value(item, 'margin')}%"] for item in scenarios]
            scenario_table = Table(scenario_rows, colWidths=[68 * mm, 36 * mm, 36 * mm, 34 * mm], repeatRows=1)
            scenario_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), SAFFRON), ("TEXTCOLOR", (0, 0), (-1, 0), INK), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("BACKGROUND", (0, 1), (-1, -1), PAPER), ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d9dfd7")), ("FONTSIZE", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("ALIGN", (1, 1), (-1, -1), "RIGHT")]))
            story.append(scenario_table)

    story += [Spacer(1, 10), Paragraph("Important: This report is decision support only. Validate local mandi price, crop inputs, treatment decisions, and any high-cost action with qualified local sources.", caption)]
    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return output.getvalue()


def recommendation_report(farm: FarmProfile) -> str:
    top = recommend(farm)[0]
    lines = [
        "Annapurna AI Crop Recommendation Report",
        "",
        f"Farmer: {farm.farmer_name}",
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
