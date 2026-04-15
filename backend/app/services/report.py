"""PDF due-diligence report generator.

Uses reportlab (pure Python, no system deps) so it runs cleanly on
Windows + Linux without Pango/Cairo installed. Produces a 1-2 page
report that mirrors the web UI: total score, per-category bars,
top reasoning bullets, raw indicators table.
"""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models.schemas import AnalysisResponse


def _score_color(score: float) -> colors.Color:
    if score >= 75:
        return colors.HexColor("#16a34a")
    if score >= 50:
        return colors.HexColor("#ca8a04")
    if score >= 25:
        return colors.HexColor("#ea580c")
    return colors.HexColor("#dc2626")


def _bar(score_0_100: float, width_mm: float = 90, height_mm: float = 5) -> Table:
    """Draw a horizontal bar inside a table cell."""
    pct = max(0.0, min(1.0, score_0_100 / 100.0))
    filled = width_mm * pct
    bar_table = Table(
        [[""]],
        colWidths=[filled * mm] if filled > 0 else [0],
        rowHeights=[height_mm * mm],
    )
    bar_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _score_color(score_0_100)),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LINEBELOW", (0, 0), (-1, -1), 0, colors.white),
            ]
        )
    )
    outer = Table(
        [[bar_table]],
        colWidths=[width_mm * mm],
        rowHeights=[height_mm * mm],
    )
    outer.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#e5e7eb")),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return outer


def render_report_pdf(analysis: AnalysisResponse) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
        title="Infrastructure Due Diligence Report",
    )
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "title", parent=base["Title"], fontSize=18, spaceAfter=4
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            parent=base["Normal"],
            textColor=colors.HexColor("#6b7280"),
            fontSize=10,
            spaceAfter=12,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontSize=12,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=10,
            spaceAfter=6,
        ),
        "body": ParagraphStyle("body", parent=base["Normal"], fontSize=10, leading=13),
        "muted": ParagraphStyle(
            "muted",
            parent=base["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#6b7280"),
            leading=11,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            parent=base["Normal"],
            fontSize=9.5,
            leading=12,
            leftIndent=10,
            bulletIndent=0,
        ),
    }

    elems: list = []
    score = analysis.score
    loc = analysis.location

    elems.append(Paragraph("Infrastructure Due Diligence Report", styles["title"]))
    elems.append(
        Paragraph(
            f"Site: {loc.lat:.4f}, {loc.lng:.4f} &nbsp;·&nbsp; "
            f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} "
            f"&nbsp;·&nbsp; Rubric v{score.version}",
            styles["subtitle"],
        )
    )

    # Big total score
    total_color = _score_color(score.total)
    total_style = ParagraphStyle(
        "total",
        parent=base["Normal"],
        fontSize=46,
        leading=50,
        textColor=total_color,
        alignment=1,
    )
    total_table = Table(
        [
            [Paragraph(f"<b>{score.total}</b>", total_style)],
            [Paragraph("overall site score / 100", styles["muted"])],
        ],
        colWidths=[17 * cm],
    )
    total_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BOX", (0, 0), (-1, -1), 1.2, total_color),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    elems.append(total_table)
    elems.append(Spacer(1, 0.4 * cm))

    # Key drivers
    elems.append(Paragraph("Key drivers", styles["h2"]))
    for r in score.reasoning:
        elems.append(Paragraph(f"• {r}", styles["bullet"]))

    # Category breakdown
    elems.append(Paragraph("Category breakdown", styles["h2"]))
    for cat in score.breakdown:
        header = Paragraph(
            f"<b>{cat.name.replace('_', ' ').title()}</b> &nbsp; "
            f"<font color='#6b7280'>weight {cat.weight * 100:.0f}%</font> &nbsp; "
            f"<b>{cat.score_0_100:.0f}/100</b>",
            styles["body"],
        )
        row = Table(
            [[header, _bar(cat.score_0_100, width_mm=70)]],
            colWidths=[9.5 * cm, 7.5 * cm],
        )
        row.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        elems.append(row)
        for rule in cat.rules:
            elems.append(Paragraph(f"— {rule.reason}", styles["muted"]))
        elems.append(Spacer(1, 0.2 * cm))

    # Raw indicators
    elems.append(Paragraph("Raw indicators", styles["h2"]))
    grid = analysis.grid_access
    en = analysis.energy
    dg = analysis.digital
    rs = analysis.resilience
    data = [
        ["Category", "Indicator", "Value"],
        ["Grid", "Nearest HV line (km)", _fmt(grid.nearest_hv_line_km)],
        ["", "Substations ≤10 km", grid.substations_10km],
        ["", "Substations ≤50 km", grid.substations_50km],
        ["", "Line density (km/km²)", f"{grid.line_density_per_km2:.4f}"],
        ["Energy", "Plants ≤50 km", en.plants_50km],
        ["", "Capacity (MW)", f"{en.total_capacity_mw_50km:.1f}"],
        ["", "Renewable share", f"{en.renewable_share * 100:.1f}%"],
        ["", "Diversity (Shannon)", f"{en.fuel_diversity_shannon:.2f}"],
        ["Digital", "Data centers ≤50 km", dg.data_centers_50km],
        ["", "Data centers ≤100 km", dg.dc_count_100km],
        ["", "Nearest DC (km)", _fmt(dg.nearest_dc_km)],
        ["Resilience", "Nearby substations", rs.nearby_nodes],
        ["", "Average degree", f"{rs.avg_degree:.2f}"],
        ["", "Nearest sub. degree", rs.nearest_substation_degree],
        ["", "Articulation pts ≤20 km", rs.articulation_points_20km],
        ["", "SPOF risk", rs.single_point_of_failure_risk],
    ]
    tbl = Table(data, colWidths=[3 * cm, 8 * cm, 6 * cm])
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (2, 1), (2, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    elems.append(tbl)

    elems.append(Spacer(1, 0.5 * cm))
    elems.append(
        Paragraph(
            "This report is generated from public geospatial datasets "
            "(WRI GPPD, OpenStreetMap) and a transparent rule-based rubric. "
            "Every number above maps to a YAML-configured scoring rule and "
            "can be reproduced end-to-end.",
            styles["muted"],
        )
    )

    doc.build(elems)
    return buf.getvalue()


def _fmt(v: float | int | None) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.2f}"
    return str(v)
