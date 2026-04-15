"""PDF due-diligence report.

Layout: single A4 page (portrait), brand header bar, two-column body.
- Left column: total score radial, key drivers, energy mix donut
- Right column: per-category bars + rule reasons
- Footer: raw indicators table + provenance disclaimer

Uses reportlab (pure Python) — no system dependencies required, so the
same code runs identically on Windows, macOS, Linux, and Docker.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.flowables import Flowable

from app.models.schemas import AnalysisResponse

PAGE_W, PAGE_H = A4
MARGIN = 1.4 * cm
HEADER_H = 1.6 * cm

ACCENT = colors.HexColor("#06b6d4")
ACCENT_2 = colors.HexColor("#8b5cf6")
INK = colors.HexColor("#0f172a")
MUTED = colors.HexColor("#64748b")
DIM = colors.HexColor("#94a3b8")
SURFACE = colors.HexColor("#f1f5f9")
BORDER = colors.HexColor("#cbd5e1")

FUEL_COLORS = {
    "solar": colors.HexColor("#fbbf24"),
    "wind": colors.HexColor("#38bdf8"),
    "hydro": colors.HexColor("#2dd4bf"),
    "gas": colors.HexColor("#f87171"),
    "oil": colors.HexColor("#991b1b"),
    "coal": colors.HexColor("#374151"),
    "nuclear": colors.HexColor("#a855f7"),
    "biomass": colors.HexColor("#84cc16"),
    "geothermal": colors.HexColor("#f97316"),
    "waste": colors.HexColor("#6b7280"),
    "other": colors.HexColor("#cbd5e1"),
    "unknown": colors.HexColor("#e2e8f0"),
}


def _score_color(s: float) -> colors.Color:
    if s >= 75:
        return colors.HexColor("#10b981")
    if s >= 50:
        return colors.HexColor("#f59e0b")
    if s >= 25:
        return colors.HexColor("#f97316")
    return colors.HexColor("#ef4444")


def _grade_letter(s: float) -> str:
    if s >= 85:
        return "A"
    if s >= 70:
        return "B"
    if s >= 55:
        return "C"
    if s >= 40:
        return "D"
    return "E"


# ---------- Header / footer ----------


def _draw_header(canvas: Canvas, doc: BaseDocTemplate) -> None:
    w, h = A4
    # Gradient-ish bar (stacked thin rectangles)
    band_h = HEADER_H
    canvas.saveState()
    steps = 40
    for i in range(steps):
        t = i / steps
        r = 6 + (139 - 6) * t
        g = 182 + (92 - 182) * t
        b = 212 + (246 - 212) * t
        canvas.setFillColorRGB(r / 255, g / 255, b / 255, alpha=0.1 + 0.02 * t)
        canvas.rect(0, h - band_h + (band_h / steps) * i, w, band_h / steps, stroke=0, fill=1)

    # Brand logo glyph (left)
    cx, cy = MARGIN + 8, h - band_h / 2
    canvas.setStrokeColor(ACCENT)
    canvas.setLineWidth(1.5)
    s = 9
    canvas.line(cx - s, cy - s * 0.6, cx, cy - s)
    canvas.line(cx, cy - s, cx + s, cy - s * 0.6)
    canvas.line(cx + s, cy - s * 0.6, cx + s, cy + s * 0.6)
    canvas.line(cx + s, cy + s * 0.6, cx, cy + s)
    canvas.line(cx, cy + s, cx - s, cy + s * 0.6)
    canvas.line(cx - s, cy + s * 0.6, cx - s, cy - s * 0.6)

    # Brand text
    canvas.setFillColor(INK)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawString(cx + s + 8, cy + 1, "GridSiteScore")
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(cx + s + 8, cy - 9, "Infrastructure due-diligence report")

    # Right side: generated timestamp
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d · %H:%M UTC")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    tw = stringWidth(ts, "Helvetica", 8)
    canvas.drawString(w - MARGIN - tw, cy - 3, ts)
    canvas.restoreState()

    # Page number in footer
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(DIM)
    canvas.drawRightString(
        w - MARGIN,
        MARGIN / 2,
        f"Page {canvas.getPageNumber()}   ·   github.com/valer0x/GRIDSITESCORE",
    )
    canvas.restoreState()


# ---------- Custom flowables ----------


class ScoreRing(Flowable):
    """A radial score indicator with a grade letter below."""

    def __init__(self, score: int, size: float = 4.2 * cm):
        super().__init__()
        self.score = max(0, min(100, score))
        self.size = size
        self.width = size
        self.height = size + 0.7 * cm

    def draw(self):
        c = self.canv
        size = self.size
        cx, cy = size / 2, size / 2 + 0.6 * cm
        r = size / 2 - 5
        stroke_w = 10
        color = _score_color(self.score)

        c.saveState()
        c.setLineWidth(stroke_w)
        c.setStrokeColor(colors.HexColor("#e2e8f0"))
        c.circle(cx, cy, r, stroke=1, fill=0)

        c.setLineWidth(stroke_w)
        c.setStrokeColor(color)
        c.setLineCap(1)
        path = c.beginPath()
        theta_start = math.pi / 2
        theta = self.score / 100.0 * 2 * math.pi
        steps = max(1, int(self.score))
        for i in range(steps + 1):
            a = theta_start - (theta * i / steps)
            x = cx + r * math.cos(a)
            y = cy + r * math.sin(a)
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        c.drawPath(path)
        c.restoreState()

        # Big number
        c.setFont("Helvetica-Bold", 30)
        c.setFillColor(color)
        num = str(int(self.score))
        nw = stringWidth(num, "Helvetica-Bold", 30)
        c.drawString(cx - nw / 2, cy - 8, num)

        c.setFont("Helvetica", 7.5)
        c.setFillColor(MUTED)
        label = "/ 100"
        lw = stringWidth(label, "Helvetica", 7.5)
        c.drawString(cx - lw / 2, cy - 20, label)

        # Grade letter
        grade = _grade_letter(self.score)
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(color)
        gw = stringWidth(f"GRADE  {grade}", "Helvetica-Bold", 9)
        c.drawString(cx - gw / 2, 8, f"GRADE  {grade}")


class EnergyMixDonut(Flowable):
    def __init__(self, mix_pct: dict[str, float], size: float = 3.6 * cm):
        super().__init__()
        self.mix = mix_pct
        self.size = size
        self.width = size + 2.8 * cm
        self.height = size

    def draw(self):
        c = self.canv
        r_outer = self.size / 2 - 2
        r_inner = r_outer * 0.55
        cx, cy = self.size / 2, self.size / 2

        items = [(k, v) for k, v in self.mix.items() if v > 0]
        if not items:
            c.setFont("Helvetica-Oblique", 8)
            c.setFillColor(DIM)
            c.drawString(cx - 20, cy - 3, "no data")
            return

        total = sum(v for _, v in items) or 1
        start = 90  # degrees
        legend_y = self.size - 2
        for fuel, v in items:
            frac = v / total
            extent = -360 * frac  # negative for clockwise
            col = FUEL_COLORS.get(fuel.lower(), FUEL_COLORS["other"])
            c.setFillColor(col)
            c.setStrokeColor(colors.white)
            c.setLineWidth(1)
            # Outer wedge
            c.wedge(
                cx - r_outer,
                cy - r_outer,
                cx + r_outer,
                cy + r_outer,
                start,
                extent,
                stroke=1,
                fill=1,
            )
            start += extent

            # Legend row
            c.setFillColor(col)
            c.rect(self.size + 4, legend_y, 7, 7, stroke=0, fill=1)
            c.setFillColor(INK)
            c.setFont("Helvetica", 7.5)
            c.drawString(self.size + 14, legend_y + 1, f"{fuel}  {v:.1f}%")
            legend_y -= 10

        # Donut hole
        c.setFillColor(colors.white)
        c.circle(cx, cy, r_inner, stroke=0, fill=1)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(cx, cy + 1, "MIX")


class CategoryBar(Flowable):
    """Icon + name + weight + score + bar + rule list (text below)."""

    def __init__(
        self,
        name: str,
        weight: float,
        score_0_100: float,
        rules: list,
        available_w: float,
    ):
        super().__init__()
        self.name = name
        self.weight = weight
        self.score = score_0_100
        self.rules = rules
        self.available_w = available_w
        self.header_h = 0.6 * cm
        self.rule_line_h = 10
        self.height = self.header_h + 4 + len(rules) * self.rule_line_h + 6
        self.width = available_w

    def draw(self):
        c = self.canv
        w = self.available_w
        color = _score_color(self.score)

        # Title row
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(INK)
        title = self.name.replace("_", " ").title()
        c.drawString(0, self.height - 11, title)

        c.setFont("Helvetica", 8)
        c.setFillColor(MUTED)
        c.drawString(
            stringWidth(title, "Helvetica-Bold", 10) + 6,
            self.height - 11,
            f"weight {self.weight * 100:.0f}%",
        )

        # Score number (right-aligned)
        score_str = f"{self.score:.0f}/100"
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(color)
        sw = stringWidth(score_str, "Helvetica-Bold", 11)
        c.drawString(w - sw, self.height - 11, score_str)

        # Bar
        bar_y = self.height - self.header_h - 2
        c.setFillColor(colors.HexColor("#e2e8f0"))
        c.roundRect(0, bar_y, w, 4, 2, stroke=0, fill=1)
        filled = w * max(0, min(1, self.score / 100.0))
        c.setFillColor(color)
        if filled > 0:
            c.roundRect(0, bar_y, filled, 4, 2, stroke=0, fill=1)

        # Rule lines
        y = bar_y - 12
        c.setFont("Helvetica", 7.5)
        for r in self.rules:
            c.setFillColor(MUTED)
            c.drawString(0, y, f"—  {r.reason}")
            y -= self.rule_line_h


# ---------- Document assembly ----------


def _fmt(v, unit: str = "") -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.2f}{(' ' + unit) if unit else ''}"
    return f"{v}{(' ' + unit) if unit else ''}"


def _raw_card(title: str, rows: list[tuple[str, str]], width: float) -> Table:
    """Compact indicator card — one per category, four rendered side-by-side."""
    data: list[list] = [[title, ""]]
    for k, v in rows:
        data.append([k, v])
    t = Table(data, colWidths=[width * 0.60, width * 0.40])
    style = [
        ("SPAN", (0, 0), (1, 0)),
        ("BACKGROUND", (0, 0), (1, 0), INK),
        ("TEXTCOLOR", (0, 0), (1, 0), ACCENT),
        ("FONTNAME", (0, 0), (1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (1, 0), 8),
        ("ALIGN", (0, 0), (1, 0), "CENTER"),
        ("TOPPADDING", (0, 0), (1, 0), 5),
        ("BOTTOMPADDING", (0, 0), (1, 0), 5),
        # body
        ("FONTSIZE", (0, 1), (-1, -1), 7.5),
        ("TEXTCOLOR", (0, 1), (0, -1), MUTED),
        ("TEXTCOLOR", (1, 1), (1, -1), INK),
        ("FONTNAME", (1, 1), (1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 1), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 3),
        ("LINEBELOW", (0, 1), (-1, -2), 0.25, BORDER),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), SURFACE))
    t.setStyle(TableStyle(style))
    return t


def _raw_indicators_row(an: AnalysisResponse, w: float) -> Table:
    gap = 4
    card_w = (w - 3 * gap) / 4
    grid = an.grid_access
    en = an.energy
    dg = an.digital
    rs = an.resilience

    grid_card = _raw_card(
        "GRID",
        [
            ("Nearest HV line (km)", _fmt(grid.nearest_hv_line_km)),
            ("Substations ≤10 km", str(grid.substations_10km)),
            ("Substations ≤50 km", str(grid.substations_50km)),
            ("Line density (km/km²)", f"{grid.line_density_per_km2:.4f}"),
        ],
        card_w,
    )
    energy_card = _raw_card(
        "ENERGY",
        [
            ("Plants ≤50 km", str(en.plants_50km)),
            ("Capacity (MW)", f"{en.total_capacity_mw_50km:.0f}"),
            ("Renewable share", f"{en.renewable_share * 100:.1f}%"),
            ("Diversity (Shannon)", f"{en.fuel_diversity_shannon:.2f}"),
        ],
        card_w,
    )
    digital_card = _raw_card(
        "DIGITAL",
        [
            ("DCs ≤50 km", str(dg.data_centers_50km)),
            ("DCs ≤100 km", str(dg.dc_count_100km)),
            ("Nearest DC (km)", _fmt(dg.nearest_dc_km)),
            ("Fiber landing (km)", _fmt(dg.fiber_landing_km)),
        ],
        card_w,
    )
    resilience_card = _raw_card(
        "RESILIENCE",
        [
            ("Graph nodes", str(rs.nearby_nodes)),
            ("Avg degree", f"{rs.avg_degree:.2f}"),
            ("Nearest sub. deg.", str(rs.nearest_substation_degree)),
            ("SPOF risk", rs.single_point_of_failure_risk.upper()),
        ],
        card_w,
    )

    row = Table(
        [[grid_card, energy_card, digital_card, resilience_card]],
        colWidths=[card_w, card_w, card_w, card_w],
    )
    row.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), gap),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return row


def render_report_pdf(analysis: AnalysisResponse) -> bytes:
    buf = BytesIO()

    doc = BaseDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN + HEADER_H,
        bottomMargin=MARGIN,
        title="GridSiteScore Due-Diligence Report",
    )
    frame = Frame(
        MARGIN,
        MARGIN,
        PAGE_W - 2 * MARGIN,
        PAGE_H - 2 * MARGIN - HEADER_H,
        showBoundary=0,
    )
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=_draw_header)])

    base = getSampleStyleSheet()
    s_title = ParagraphStyle(
        "t", parent=base["Title"], fontSize=15, leading=18, spaceAfter=2, textColor=INK
    )
    s_sub = ParagraphStyle(
        "sub",
        parent=base["Normal"],
        fontSize=9,
        leading=12,
        textColor=MUTED,
        spaceAfter=8,
    )
    s_h2 = ParagraphStyle(
        "h2",
        parent=base["Heading3"],
        fontSize=9.5,
        textColor=ACCENT,
        spaceBefore=8,
        spaceAfter=4,
        leading=11,
    )
    s_body = ParagraphStyle(
        "b",
        parent=base["Normal"],
        fontSize=9,
        leading=12,
        textColor=INK,
        spaceAfter=2,
    )
    s_bullet = ParagraphStyle(
        "bul",
        parent=base["Normal"],
        fontSize=8.5,
        leading=11,
        leftIndent=10,
        textColor=INK,
    )
    s_muted = ParagraphStyle(
        "m", parent=base["Normal"], fontSize=8, textColor=MUTED, leading=10
    )

    elems: list = []
    loc = analysis.location
    score = analysis.score

    # Title block
    elems.append(
        Paragraph(
            f"Site analysis · <font color='#06b6d4'>{loc.lat:.4f}, {loc.lng:.4f}</font>",
            s_title,
        )
    )
    elems.append(
        Paragraph(
            f"Weighted score across grid access, energy, digital and resilience "
            f"— rubric v{score.version}.",
            s_sub,
        )
    )

    # Two-column top section: left = ring + key drivers + energy mix;
    # right = category bars. Nested Tables enforce column width so
    # Paragraphs inside wrap correctly.
    inner_w = PAGE_W - 2 * MARGIN
    col_gap = 0.4 * cm
    left_w = (inner_w - col_gap) * 0.38
    right_w = (inner_w - col_gap) * 0.62

    def _stack(items: list, width: float) -> Table:
        rows = [[it] for it in items]
        t = Table(rows, colWidths=[width])
        t.setStyle(
            TableStyle(
                [
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        return t

    left_items: list = [
        ScoreRing(score.total),
        Spacer(1, 0.25 * cm),
        Paragraph("Key drivers", s_h2),
    ]
    for r in score.reasoning:
        left_items.append(Paragraph(f"•  {r}", s_bullet))
    left_items.append(Spacer(1, 0.3 * cm))
    left_items.append(Paragraph("Energy mix (≤ 50 km)", s_h2))
    left_items.append(EnergyMixDonut(analysis.energy.mix_pct))

    right_items: list = [Paragraph("Category breakdown", s_h2)]
    for cat in score.breakdown:
        right_items.append(
            CategoryBar(
                cat.name, cat.weight, cat.score_0_100, cat.rules, right_w
            )
        )
        right_items.append(Spacer(1, 0.18 * cm))

    # 3-column layout: [left content] [literal gap] [right content].
    # A dedicated gap column removes any chance of bullet overflow.
    col_table = Table(
        [[_stack(left_items, left_w), "", _stack(right_items, right_w)]],
        colWidths=[left_w, col_gap, right_w],
    )
    col_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    elems.append(col_table)
    elems.append(Spacer(1, 0.35 * cm))

    # Raw indicators — 4 side-by-side cards, no page break
    elems.append(Paragraph("Raw indicators", s_h2))
    elems.append(_raw_indicators_row(analysis, inner_w))

    # Footer disclaimer
    elems.append(Spacer(1, 0.4 * cm))
    elems.append(
        Paragraph(
            "Data: WRI Global Power Plant Database (CC BY 4.0), OpenStreetMap (ODbL), "
            "curated data-center fixture. Scoring: rule-based, YAML-configured "
            "(see <font face='Helvetica-Bold'>scoring_config.yaml</font>). Every number "
            "above is reproducible from the raw indicators via the transparent rubric.",
            s_muted,
        )
    )

    doc.build(elems)
    return buf.getvalue()
