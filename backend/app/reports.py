"""Text and PDF reports.

Both reports now carry the things the farmer needs in order to judge the numbers: the verdict and
any disqualifying limiter, the yield and profit ranges rather than a single figure, and where the
price came from. A printed report is the artefact that gets taken to a bank or a buyer, so a bare
profit number on it is the most consequential place to overstate confidence.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any
from xml.sax.saxutils import escape as xml_escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .crop_data import provenance
from .recommender import recommend
from .schemas import FarmProfile, PdfReportRequest

FOREST = colors.HexColor("#173f36")
SAFFRON = colors.HexColor("#d58b2b")
PAPER = colors.HexColor("#fbfaf4")
INK = colors.HexColor("#1d2a28")
MUTED = colors.HexColor("#64716c")
RULE = colors.HexColor("#d9dfd7")

DISCLAIMER = (
    "Decision support only. Yield, price and profit are planning estimates, not guarantees, and "
    "this report is not lending, credit, or investment advice. Verify the local mandi price, input "
    "costs, and any treatment or high-cost decision with a qualified local source before acting."
)


# ReportLab parses a Paragraph's text as its own mini-markup, so anything reaching one
# unescaped is code rather than text: `<img src="/etc/passwd"/>` makes the server read a local
# file into the PDF, and an unbalanced `<b>` raises and returns a 500. Every value originating
# outside this module is escaped, and lists are bounded so one request cannot ask the shared
# thread pool to lay out a 60,000-row document.
MAX_LIST_ITEMS = 12
MAX_TEXT = 500
MAX_TABLE_ROWS = 40


def safe(value: Any, limit: int = MAX_TEXT) -> str:
    """XML-escape untrusted text and bound its length before it reaches a PDF cell."""
    text = "" if value is None else str(value)
    if len(text) > limit:
        text = text[: limit - 1] + "\u2026"
    return xml_escape(text)


def safe_list(values: Any, limit: int = MAX_LIST_ITEMS) -> list[str]:
    if not isinstance(values, (list, tuple)):
        return []
    return [safe(item, 240) for item in values[:limit]]


def _inr(value: Any) -> str:
    try:
        return f"INR {round(float(value)):,}"
    except (TypeError, ValueError):
        return "Not available"


def _value(source: dict[str, Any] | None, key: str, default: str = "Not available") -> str:
    if not source or source.get(key) in (None, ""):
        return default
    return safe(source[key], 160)


def _table(rows: list[list[str]], widths: list[float], header: bool = False, right_align_from: int | None = None):
    table = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("BACKGROUND", (0, 1 if header else 0), (-1, -1), PAPER),
        ("GRID", (0, 0), (-1, -1), 0.4, RULE),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), FOREST),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    else:
        style += [
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("TEXTCOLOR", (0, 0), (0, -1), FOREST),
        ]
        if len(rows[0]) > 2:
            style += [("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"), ("TEXTCOLOR", (2, 0), (2, -1), FOREST)]
    if right_align_from is not None:
        style.append(("ALIGN", (right_align_from, 1), (-1, -1), "RIGHT"))
    table.setStyle(TableStyle(style))
    return table


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(RULE)
    canvas.line(18 * mm, 14 * mm, 192 * mm, 14 * mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 9 * mm, "Annapurna AI - planning estimates, not guarantees")
    canvas.drawRightString(192 * mm, 9 * mm, f"Page {doc.page}")
    canvas.restoreState()


def resolve_recommendation(request: PdfReportRequest, prices: dict[str, int] | None = None):
    """Recompute the recommendation for the requested crop from the farm profile.

    Returns the server's own ranking entry, never the client's. Raises ValueError when the crop
    is not one this product covers.
    """
    ranked = recommend(request.farm, prices)
    wanted = request.requested_crop
    if wanted is None:
        return ranked[0]
    match = next((item for item in ranked if item.crop.casefold() == wanted.casefold()), None)
    if match is None:
        raise ValueError(
            f"'{wanted}' is not a crop this report covers. Choose one of: {', '.join(item.crop for item in ranked)}"
        )
    return match


def pdf_report(request: PdfReportRequest, prices: dict[str, int] | None = None) -> bytes:
    """A printable farm and finance report, built from the server's own analysis."""
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
    title = ParagraphStyle(
        "T", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=24, leading=29, textColor=FOREST, spaceAfter=3
    )
    subtitle = ParagraphStyle("S", parent=styles["Normal"], fontSize=9, leading=13, textColor=MUTED, spaceAfter=13)
    heading = ParagraphStyle(
        "H",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12.5,
        leading=17,
        textColor=FOREST,
        spaceBefore=11,
        spaceAfter=6,
    )
    body = ParagraphStyle("B", parent=styles["BodyText"], fontSize=9, leading=13.5, textColor=INK)
    caption = ParagraphStyle("C", parent=body, fontSize=7.8, leading=10.5, textColor=MUTED)
    warn = ParagraphStyle("W", parent=body, fontSize=9, leading=13.5, textColor=colors.HexColor("#8c3b1c"))

    farm = request.farm
    crop = resolve_recommendation(request, prices)
    economics = crop.economics

    story = [
        Paragraph(
            "ANNAPURNA AI",
            ParagraphStyle(
                "Brand", parent=body, fontName="Helvetica-Bold", fontSize=8, textColor=SAFFRON, alignment=TA_CENTER
            ),
        ),
        Paragraph("Farm Decision &amp; Season Finance Report", title),
        Paragraph(
            "Built from your farm profile and the latest analysis. Every figure below is a planning "
            "estimate; the basis of each one is stated.",
            subtitle,
        ),
        Paragraph("Farm profile", heading),
        _table(
            [
                ["Farmer", safe(farm.farmer_name, 80), "Location", safe(farm.location, 120)],
                ["Season", farm.season, "Land size", f"{farm.land_size:g} acre"],
                ["Soil", safe(farm.soil_type, 30), "Irrigation", safe(farm.irrigation, 20)],
                ["Previous crop", safe(farm.previous_crop, 40), "Planning budget", _inr(farm.budget)],
            ],
            [28 * mm, 57 * mm, 32 * mm, 57 * mm],
        ),
        Paragraph("Crop recommendation", heading),
    ]

    story.append(
        _table(
            [
                [
                    "Recommended crop",
                    safe(crop.crop, 50),
                    "Suitability",
                    f"{crop.suitability}% - {safe(crop.verdict, 40)}",
                ],
                ["Season length", f"about {crop.duration_days} days", "Water need", crop.water],
                ["Planning price", f"{_inr(crop.market_price)}/quintal", "Price basis", safe(crop.price_basis, 90)],
            ],
            [35 * mm, 50 * mm, 35 * mm, 54 * mm],
        )
    )

    if crop.limiters:
        story += [
            Spacer(1, 6),
            Paragraph("<b>Why this crop is limited:</b>", warn),
            *[Paragraph(f"&bull; {item}", warn) for item in safe_list(crop.limiters)],
        ]

    story += [
        Paragraph("Expected range", heading),
        _table(
            [
                ["", "Poor season", "Typical", "Good season"],
                [
                    "Yield (quintal)",
                    f"{economics.expected_yield_quintal.low:g}",
                    f"{economics.expected_yield_quintal.typical:g}",
                    f"{economics.expected_yield_quintal.high:g}",
                ],
                [
                    "Cost",
                    _inr(economics.estimated_cost_inr.high),
                    _inr(economics.estimated_cost_inr.typical),
                    _inr(economics.estimated_cost_inr.low),
                ],
                [
                    "Revenue",
                    _inr(economics.estimated_revenue_inr.low),
                    _inr(economics.estimated_revenue_inr.typical),
                    _inr(economics.estimated_revenue_inr.high),
                ],
                [
                    "Profit",
                    _inr(economics.expected_profit_inr.low),
                    _inr(economics.expected_profit_inr.typical),
                    _inr(economics.expected_profit_inr.high),
                ],
            ],
            [44 * mm, 33 * mm, 33 * mm, 34 * mm],
            header=True,
            right_align_from=1,
        ),
        Spacer(1, 6),
        Paragraph(
            "The poor-season column pairs a low yield with a high cost, and the good season the "
            "reverse. Plan against the poor-season column, not the typical one.",
            caption,
        ),
        Spacer(1, 7),
        Paragraph(
            f"<b>Why this crop:</b> {'; '.join(safe_list(crop.reasons)) or 'No specific reason recorded.'}", body
        ),
        Paragraph(f"<b>Watch:</b> {'; '.join(safe_list(crop.cautions)) or 'No additional caution returned.'}", body),
        Paragraph(f"<b>Advisory:</b> {safe(crop.advisory)}", body),
        Paragraph(f"<b>Rotation:</b> {safe(crop.rotation)}", body),
    ]

    weather = request.weather or {}
    market = request.market or {}
    story += [
        Paragraph("Data sources used", heading),
        _table(
            [
                ["Weather", _value(weather, "source"), "Market", _value(market, "source")],
                [
                    "Temperature",
                    f"{_value(weather, 'temperature')} C",
                    "Modal price",
                    f"{_inr(market.get('modal_price_per_quintal'))}/quintal",
                ],
                [
                    "Weather note",
                    _value(weather, "alert"),
                    "Mandi / date",
                    f"{_value(market, 'market')} / {_value(market, 'observed_at')}",
                ],
            ],
            [30 * mm, 55 * mm, 30 * mm, 59 * mm],
        ),
    ]

    finance = request.finance or {}
    if finance:
        summary = finance.get("summary") or {}
        story += [
            Paragraph("Season finance", heading),
            _table(
                [
                    [
                        "Working capital",
                        _inr(summary.get("actual_cost")),
                        "Peak cash needed",
                        _inr(summary.get("peak_working_capital")),
                    ],
                    [
                        "Expected revenue",
                        _inr(summary.get("expected_revenue")),
                        "Expected profit",
                        _inr(summary.get("expected_profit")),
                    ],
                    [
                        "Break-even price",
                        f"{_inr(summary.get('break_even_price_per_quintal'))}/quintal",
                        "Worst case",
                        f"{_inr(summary.get('worst_case_profit'))} ({_value(summary, 'worst_case_name', 'n/a')})",
                    ],
                ],
                [32 * mm, 52 * mm, 32 * mm, 58 * mm],
            ),
        ]
        expenses = finance.get("expenses") or []
        if expenses:
            story += [
                Paragraph("Expense tracker", heading),
                _table(
                    [["Category", "Planned", "Tracked", "Variance"]]
                    + [
                        [
                            _value(item, "category"),
                            _inr(item.get("planned")),
                            _inr(item.get("actual")),
                            _inr(item.get("variance")),
                        ]
                        for item in expenses[:MAX_TABLE_ROWS]
                    ],
                    [66 * mm, 34 * mm, 34 * mm, 40 * mm],
                    header=True,
                    right_align_from=1,
                ),
            ]
        scenarios = finance.get("scenarios") or []
        if scenarios:
            story += [
                Paragraph("Risk scenarios", heading),
                _table(
                    [["Scenario", "Revenue", "Cost", "Profit"]]
                    + [
                        [
                            _value(item, "name"),
                            _inr(item.get("revenue")),
                            _inr(item.get("cost")),
                            _inr(item.get("profit")),
                        ]
                        for item in scenarios[:MAX_TABLE_ROWS]
                    ],
                    [60 * mm, 38 * mm, 38 * mm, 38 * mm],
                    header=True,
                    right_align_from=1,
                ),
            ]

    reference = provenance()
    story += [
        Spacer(1, 10),
        KeepTogether(
            [
                Paragraph(
                    f"<b>Reference data:</b> {reference['region']}. Prices for {reference['price_season']}, "
                    f"last reviewed {reference['last_reviewed']}.",
                    caption,
                ),
                *(
                    [Paragraph(f"<b>Sources:</b> {'; '.join(safe_list(crop.sources))}", caption)]
                    if crop.sources
                    else []
                ),
                Spacer(1, 5),
                Paragraph(f"<b>Important:</b> {DISCLAIMER}", caption),
            ]
        ),
    ]
    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return output.getvalue()


def recommendation_report(farm: FarmProfile, prices: dict[str, int] | None = None) -> str:
    """A plain-text report, for printing or sharing over a messaging app."""
    ranked = recommend(farm, prices)
    top = ranked[0]
    economics = top.economics
    reference = provenance()

    lines = [
        "ANNAPURNA AI - CROP RECOMMENDATION REPORT",
        "=" * 48,
        "",
        "YOUR FARM",
        f"  Farmer        : {farm.farmer_name}",
        f"  Location      : {farm.location}",
        f"  Season        : {farm.season}",
        f"  Land size     : {farm.land_size:g} acre",
        f"  Soil          : {farm.soil_type} (pH {farm.ph:g})",
        f"  Irrigation    : {farm.irrigation}",
        f"  Previous crop : {farm.previous_crop}",
        f"  Budget        : INR {farm.budget:,.0f}",
        "",
        f"RECOMMENDED: {top.crop.upper()}  -  {top.suitability}% ({top.verdict})",
        f"  Season length : about {top.duration_days} days",
        f"  Water need    : {top.water}",
        f"  Planning price: INR {top.market_price:,}/quintal  [{top.price_basis}]",
        "",
        "  EXPECTED RANGE            poor season       typical      good season",
        f"    Yield (quintal)  {economics.expected_yield_quintal.low:>12g}  {economics.expected_yield_quintal.typical:>12g}  {economics.expected_yield_quintal.high:>14g}",
        f"    Cost (INR)       {economics.estimated_cost_inr.high:>12,.0f}  {economics.estimated_cost_inr.typical:>12,.0f}  {economics.estimated_cost_inr.low:>14,.0f}",
        f"    Revenue (INR)    {economics.estimated_revenue_inr.low:>12,.0f}  {economics.estimated_revenue_inr.typical:>12,.0f}  {economics.estimated_revenue_inr.high:>14,.0f}",
        f"    Profit (INR)     {economics.expected_profit_inr.low:>12,.0f}  {economics.expected_profit_inr.typical:>12,.0f}  {economics.expected_profit_inr.high:>14,.0f}",
        "",
        f"  Sustainability: {top.sustainability_score}/100",
        "",
    ]

    if top.limiters:
        lines += ["WHY THIS CROP IS LIMITED", *[f"  - {item}" for item in top.limiters], ""]

    lines += [
        "WHY THIS CROP",
        *[f"  - {reason}" for reason in top.reasons],
        "",
        "WATCH OUT FOR",
        *[f"  - {caution}" for caution in top.cautions],
        "",
        "ADVISORY",
        f"  {top.advisory}",
        f"  Rotation: {top.rotation}",
        f"  Sustainability: {top.sustainability}",
        "",
        "OTHER OPTIONS CONSIDERED",
        *[
            f"  {item.suitability:>3}%  {item.crop:<14} {item.verdict}"
            + (f"  ({item.limiters[0]})" if item.limiters else "")
            for item in ranked[1:]
        ],
        "",
        "REFERENCE DATA",
        f"  Region : {reference['region']}",
        f"  Prices : {reference['price_season']}, last reviewed {reference['last_reviewed']}",
        *[f"  Source : {source}" for source in top.sources],
        "",
        "IMPORTANT",
        f"  {DISCLAIMER}",
    ]
    return "\n".join(lines)
