"""Platypus PDF renderer for CNAS investigation reports.

Renders the existing report payload as a professional investigator-facing
document. It does not add conclusions or change recorded values.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    CondPageBreak,
    KeepTogether,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Restrained investigator-document palette.
INK = colors.HexColor("#1B2430")
MUTED = colors.HexColor("#5B6570")
LINE = colors.HexColor("#D0D6DE")
BAND = colors.HexColor("#1B2A41")
ACCENT = colors.HexColor("#2C4663")
HEADER_BG = colors.HexColor("#E7EDF3")
ALT_ROW = colors.HexColor("#F5F7F9")
EMPTY_BG = colors.HexColor("#F7F8FA")
WHITE = colors.white

PAGE_WIDTH, PAGE_HEIGHT = A4
LEFT_MARGIN = 0.7 * inch
RIGHT_MARGIN = 0.7 * inch
TOP_MARGIN = 0.78 * inch
BOTTOM_MARGIN = 0.68 * inch
CONTENT_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN

EMPTY_LABEL = "None recorded."
DISCLAIMER = (
    "This document restates recorded CNAS data. It does not assert guilt, "
    "ownership, or conclusions beyond the stored records."
)


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "kicker": ParagraphStyle(
            "CNASKicker",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=ACCENT,
            spaceAfter=2,
        ),
        "title": ParagraphStyle(
            "CNASTitle",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=INK,
            spaceAfter=6,
        ),
        "disclaimer": ParagraphStyle(
            "CNASDisclaimer",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=11,
            textColor=MUTED,
            spaceAfter=10,
        ),
        "section": ParagraphStyle(
            "CNASSection",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=13,
            textColor=INK,
            spaceBefore=9,
            spaceAfter=4,
            keepWithNext=True,
            borderPadding=0,
        ),
        "subsection": ParagraphStyle(
            "CNASSubsection",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=ACCENT,
            spaceBefore=7,
            spaceAfter=3,
            keepWithNext=False,
        ),
        "meta": ParagraphStyle(
            "CNASMeta",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=INK,
        ),
        "cell": ParagraphStyle(
            "CNASCell",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10.5,
            textColor=INK,
            alignment=TA_LEFT,
        ),
        "cell_header": ParagraphStyle(
            "CNASCellHeader",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=10,
            textColor=WHITE,
            alignment=TA_LEFT,
        ),
        "metric_value": ParagraphStyle(
            "CNASMetricValue",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=13,
            textColor=INK,
            alignment=TA_LEFT,
        ),
        "metric_label": ParagraphStyle(
            "CNASMetricLabel",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=9,
            textColor=MUTED,
            alignment=TA_LEFT,
        ),
        "empty": ParagraphStyle(
            "CNASEmpty",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8.5,
            leading=11,
            textColor=MUTED,
        ),
        "limit": ParagraphStyle(
            "CNASLimit",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11.5,
            textColor=INK,
        ),
    }


def _display(value: Any) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        if value == int(value) and abs(value) < 1_000_000:
            return str(int(value))
        return f"{value:.4g}"
    if isinstance(value, list):
        if not value:
            return "—"
        return ", ".join(_display(item) for item in value)
    if isinstance(value, dict):
        parts = [
            f"{key}={_display(item)}"
            for key, item in value.items()
            if item not in (None, "", [])
        ]
        return "; ".join(parts) if parts else "—"
    return str(value)


def _p(value: Any, style: ParagraphStyle) -> Paragraph:
    text = escape(_display(value))
    return Paragraph(text.replace("\n", "<br/>"), style)


def _empty_state(styles: dict[str, ParagraphStyle]) -> Table:
    table = Table(
        [[Paragraph(EMPTY_LABEL, styles["empty"])]],
        colWidths=[CONTENT_WIDTH],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), EMPTY_BG),
                ("BOX", (0, 0), (-1, -1), 0.4, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    table.hAlign = "LEFT"
    return table


def _table_style(*, header: bool = True, key_column: bool = False) -> TableStyle:
    commands: list[tuple] = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.3, LINE),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
    ]
    if header:
        commands.extend(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 7.5),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, ALT_ROW]),
            ]
        )
    elif key_column:
        commands.extend(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (0, -1), 7.5),
                ("TEXTCOLOR", (0, 0), (0, -1), MUTED),
                ("BACKGROUND", (0, 0), (0, -1), HEADER_BG),
                ("BACKGROUND", (1, 0), (1, -1), WHITE),
            ]
        )
    else:
        commands.append(("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, ALT_ROW]))
    return TableStyle(commands)


def _data_table(
    headers: list[str],
    rows: list[list[Any]],
    col_widths: list[float],
    styles: dict[str, ParagraphStyle],
) -> Table:
    data = [[_p(header, styles["cell_header"]) for header in headers]]
    for row in rows:
        data.append([_p(cell, styles["cell"]) for cell in row])
    table = Table(data, colWidths=col_widths, repeatRows=1, splitByRow=1)
    table.setStyle(_table_style(header=True))
    table.hAlign = "LEFT"
    table.spaceAfter = 2
    return table


def _kv_table(
    pairs: list[tuple[str, Any]],
    styles: dict[str, ParagraphStyle],
) -> Table:
    data = [
        [_p(label, styles["cell"]), _p(value, styles["cell"])]
        for label, value in pairs
    ]
    table = Table(
        data,
        colWidths=[CONTENT_WIDTH * 0.28, CONTENT_WIDTH * 0.72],
        repeatRows=0,
        splitByRow=1,
    )
    table.setStyle(_table_style(header=False, key_column=True))
    table.hAlign = "LEFT"
    return table


def _metric_strip(
    metrics: list[tuple[str, Any]],
    styles: dict[str, ParagraphStyle],
) -> Table:
    width = CONTENT_WIDTH / max(len(metrics), 1)
    cells = []
    for label, value in metrics:
        inner = Table(
            [
                [Paragraph(escape(_display(value)), styles["metric_value"])],
                [Paragraph(escape(label), styles["metric_label"])],
            ],
            colWidths=[width - 8],
        )
        inner.setStyle(
            TableStyle(
                [
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (0, 0), 7),
                    ("BOTTOMPADDING", (0, -1), (0, -1), 6),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BACKGROUND", (0, 0), (-1, -1), HEADER_BG),
                ]
            )
        )
        cells.append(inner)
    table = Table([cells], colWidths=[width] * len(metrics))
    table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.4, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    table.hAlign = "LEFT"
    return table


def _section(
    title: str,
    body: Any,
    styles: dict[str, ParagraphStyle],
    *,
    keep: bool = False,
) -> list[Any]:
    heading = Paragraph(escape(title), styles["section"])
    if keep:
        return [KeepTogether([heading, body])]
    return [heading, body]


def _investigator_label(investigator: dict[str, Any] | None) -> str:
    if not investigator:
        return "—"
    username = investigator.get("username")
    role = investigator.get("role")
    if username and role:
        return f"{username} ({role})"
    return _display(username or role)


def _window(investigation: dict[str, Any]) -> str:
    start = investigation.get("from_datetime")
    end = investigation.get("to_datetime")
    if not start and not end:
        return "—"
    return f"{_display(start)} → {_display(end)}"


def _draw_chrome(
    canvas,
    doc,
    *,
    report_name: str,
    generated_at: str,
) -> None:
    canvas.saveState()
    canvas.setFillColor(BAND)
    canvas.rect(0, PAGE_HEIGHT - 16, PAGE_WIDTH, 16, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(LEFT_MARGIN, PAGE_HEIGHT - 11, "CNAS  ·  Criminal Network Analysis System")
    canvas.drawRightString(
        PAGE_WIDTH - RIGHT_MARGIN,
        PAGE_HEIGHT - 11,
        _display(generated_at),
    )

    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.4)
    canvas.line(LEFT_MARGIN, 0.46 * inch, PAGE_WIDTH - RIGHT_MARGIN, 0.46 * inch)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7.5)
    name = report_name if len(report_name) <= 72 else report_name[:69] + "..."
    canvas.drawString(LEFT_MARGIN, 0.30 * inch, name)
    canvas.drawRightString(
        PAGE_WIDTH - RIGHT_MARGIN,
        0.30 * inch,
        f"Page {doc.page}",
    )
    canvas.restoreState()


def _title_block(payload: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    generated_by = payload.get("generated_by") or {}
    source = payload.get("source") or {}
    return [
        Paragraph("INVESTIGATOR REPORT", styles["kicker"]),
        Paragraph("CNAS INVESTIGATION REPORT", styles["title"]),
        Paragraph(DISCLAIMER, styles["disclaimer"]),
        _kv_table(
            [
                ("Generated at", payload.get("generated_at")),
                (
                    "Generated by",
                    _investigator_label(generated_by)
                    if generated_by
                    else "—",
                ),
                ("Source", f"{_display(source.get('type'))}  {_display(source.get('id'))}"),
                ("Report ID", payload.get("report_id")),
            ],
            styles,
        ),
    ]


def _investigation_section(payload: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    investigation = payload.get("investigation") or {}
    table = _kv_table(
        [
            ("Name", investigation.get("name")),
            ("Description", investigation.get("description")),
            ("Jurisdiction", payload.get("jurisdiction")),
            ("Investigator", _investigator_label(payload.get("investigator"))),
            ("Temporal window", _window(investigation)),
            ("Selected entities", investigation.get("selected_entity_ids")),
            ("Graph seeds", investigation.get("graph_seeds")),
            ("Investigation ID", investigation.get("id")),
        ],
        styles,
    )
    return _section("Investigation", table, styles, keep=True)


def _cases_section(payload: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    cases = payload.get("cases") or []
    if not cases:
        return _section("Cases / FIR", _empty_state(styles), styles, keep=True)
    widths = [
        CONTENT_WIDTH * 0.16,
        CONTENT_WIDTH * 0.20,
        CONTENT_WIDTH * 0.14,
        CONTENT_WIDTH * 0.18,
        CONTENT_WIDTH * 0.12,
        CONTENT_WIDTH * 0.20,
    ]
    rows = [
        [
            case.get("fir_id"),
            case.get("crime"),
            case.get("date"),
            case.get("location"),
            case.get("person_id"),
            (case.get("involved_person") or {}).get("name"),
        ]
        for case in cases
    ]
    table = _data_table(
        ["FIR ID", "Crime", "Date", "Location", "Person ID", "Involved person"],
        rows,
        widths,
        styles,
    )
    return _section("Cases / FIR", table, styles)


def _people_section(payload: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    people = payload.get("people") or []
    vehicles = (payload.get("entities") or {}).get("vehicles") or []
    flowables: list[Any] = [Paragraph("People / Entities", styles["section"])]
    if not people:
        flowables.append(_empty_state(styles))
    else:
        widths = [
            CONTENT_WIDTH * 0.14,
            CONTENT_WIDTH * 0.28,
            CONTENT_WIDTH * 0.22,
            CONTENT_WIDTH * 0.20,
            CONTENT_WIDTH * 0.16,
        ]
        rows = [
            [
                person.get("person_id") or person.get("entity_id"),
                person.get("name"),
                person.get("phone"),
                person.get("home_city"),
                person.get("risk_group"),
            ]
            for person in people
        ]
        flowables.append(
            _data_table(
                ["Person ID", "Name", "Phone", "Home city", "Risk group"],
                rows,
                widths,
                styles,
            )
        )
    if vehicles:
        flowables.append(Paragraph("Vehicles", styles["subsection"]))
        v_widths = [
            CONTENT_WIDTH * 0.22,
            CONTENT_WIDTH * 0.28,
            CONTENT_WIDTH * 0.25,
            CONTENT_WIDTH * 0.25,
        ]
        v_rows = [
            [
                vehicle.get("person_id"),
                vehicle.get("vehicle_no"),
                vehicle.get("registered_city"),
                vehicle.get("vehicle_type"),
            ]
            for vehicle in vehicles
        ]
        flowables.append(
            _data_table(
                ["Person ID", "Registration", "Registered city", "Type"],
                v_rows,
                v_widths,
                styles,
            )
        )
    return flowables


def _network_section(payload: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    network = payload.get("network_summary") or {}
    global_stats = network.get("global") or {}
    relationships = list(network.get("relationships") or [])
    metrics = _metric_strip(
        [
            ("In-scope nodes", network.get("in_scope_nodes")),
            ("In-scope relationships", network.get("in_scope_relationships")),
            ("Global nodes", global_stats.get("nodes")),
            ("Global edges", global_stats.get("edges")),
        ],
        styles,
    )
    flowables: list[Any] = _section("Network summary", metrics, styles, keep=True)
    flowables.append(CondPageBreak(82))
    heading = Paragraph("Relationships", styles["subsection"])
    if not relationships:
        flowables.append(KeepTogether([heading, _empty_state(styles)]))
        return flowables
    flowables.append(heading)

    widths = [CONTENT_WIDTH * 0.32, CONTENT_WIDTH * 0.36, CONTENT_WIDTH * 0.32]
    rows = [
        [rel.get("source"), rel.get("relationship"), rel.get("target")]
        for rel in relationships
    ]
    flowables.append(
        _data_table(
            ["Source", "Relationship", "Target"],
            rows,
            widths,
            styles,
        )
    )
    return flowables


def _analytics_section(payload: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    analytics = payload.get("analytics") or {}
    flowables: list[Any] = [Paragraph("Analytics findings", styles["section"])]

    risk_rows = analytics.get("risk") or []
    risk_heading = Paragraph("Risk", styles["subsection"])
    if not risk_rows:
        flowables.append(KeepTogether([risk_heading, _empty_state(styles)]))
    else:
        flowables.append(risk_heading)
        flowables.append(
            _data_table(
                ["Entity ID", "Name", "Score", "Level", "Method"],
                [
                    [
                        row.get("entity_id"),
                        row.get("name"),
                        row.get("risk_score"),
                        row.get("risk_level"),
                        row.get("scoring_method"),
                    ]
                    for row in risk_rows
                ],
                [
                    CONTENT_WIDTH * 0.16,
                    CONTENT_WIDTH * 0.26,
                    CONTENT_WIDTH * 0.12,
                    CONTENT_WIDTH * 0.14,
                    CONTENT_WIDTH * 0.32,
                ],
                styles,
            )
        )

    anomaly_rows = analytics.get("anomalies") or []
    anomaly_heading = Paragraph("Anomalies", styles["subsection"])
    if not anomaly_rows:
        flowables.append(KeepTogether([anomaly_heading, _empty_state(styles)]))
    else:
        flowables.append(anomaly_heading)
        flowables.append(
            _data_table(
                ["Entity ID", "Name", "Score", "Level", "Method"],
                [
                    [
                        row.get("entity_id"),
                        row.get("name"),
                        row.get("anomaly_score"),
                        row.get("anomaly_level"),
                        row.get("method"),
                    ]
                    for row in anomaly_rows
                ],
                [
                    CONTENT_WIDTH * 0.16,
                    CONTENT_WIDTH * 0.26,
                    CONTENT_WIDTH * 0.12,
                    CONTENT_WIDTH * 0.14,
                    CONTENT_WIDTH * 0.32,
                ],
                styles,
            )
        )

    centrality_rows = analytics.get("centrality") or []
    centrality_heading = Paragraph("Centrality", styles["subsection"])
    if not centrality_rows:
        flowables.append(KeepTogether([centrality_heading, _empty_state(styles)]))
    else:
        flowables.append(centrality_heading)
        flowables.append(
            _data_table(
                ["Entity ID", "Name", "Degree", "Betweenness", "PageRank"],
                [
                    [
                        row.get("entity_id"),
                        row.get("name"),
                        row.get("degree_centrality"),
                        row.get("betweenness_centrality"),
                        row.get("pagerank"),
                    ]
                    for row in centrality_rows
                ],
                [
                    CONTENT_WIDTH * 0.16,
                    CONTENT_WIDTH * 0.28,
                    CONTENT_WIDTH * 0.18,
                    CONTENT_WIDTH * 0.20,
                    CONTENT_WIDTH * 0.18,
                ],
                styles,
            )
        )
    return flowables


def _an2_section(payload: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    findings = payload.get("an2_findings") or []
    if not findings:
        return _section("AN-2 findings", _empty_state(styles), styles, keep=True)
    rows = [
        [
            finding.get("finding_id"),
            finding.get("claim"),
            finding.get("confidence"),
            finding.get("cases"),
            finding.get("jurisdictions"),
        ]
        for finding in findings
    ]
    table = _data_table(
        ["Finding ID", "Recorded claim", "Confidence", "Cases", "Jurisdictions"],
        rows,
        [
            CONTENT_WIDTH * 0.18,
            CONTENT_WIDTH * 0.38,
            CONTENT_WIDTH * 0.12,
            CONTENT_WIDTH * 0.16,
            CONTENT_WIDTH * 0.16,
        ],
        styles,
    )
    return _section("AN-2 findings", table, styles)


def _adjudication_section(payload: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    reviews = payload.get("adjudication") or []
    if not reviews:
        return _section("Adjudication decisions", _empty_state(styles), styles, keep=True)
    rows = [
        [
            review.get("review_id") or review.get("id"),
            review.get("status"),
            review.get("candidate_value"),
            review.get("entity_type"),
            review.get("confirmed_entity_id"),
            review.get("decision_reason"),
        ]
        for review in reviews
    ]
    table = _data_table(
        ["Review ID", "Status", "Candidate", "Type", "Confirmed ID", "Reason"],
        rows,
        [
            CONTENT_WIDTH * 0.22,
            CONTENT_WIDTH * 0.12,
            CONTENT_WIDTH * 0.18,
            CONTENT_WIDTH * 0.12,
            CONTENT_WIDTH * 0.14,
            CONTENT_WIDTH * 0.22,
        ],
        styles,
    )
    return _section("Adjudication decisions", table, styles)


def _evidence_section(payload: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    evidence = payload.get("evidence") or []
    if not evidence:
        return _section("Evidence / provenance", _empty_state(styles), styles, keep=True)
    rows = [
        [
            item.get("source"),
            item.get("source_ref"),
            item.get("entity_id") or item.get("person_id"),
            item.get("entity_type"),
            item.get("content_hash"),
            item.get("ingested_at"),
        ]
        for item in evidence
    ]
    table = _data_table(
        ["Source", "Source ref", "Entity ID", "Type", "Content hash", "Ingested at"],
        rows,
        [
            CONTENT_WIDTH * 0.16,
            CONTENT_WIDTH * 0.16,
            CONTENT_WIDTH * 0.14,
            CONTENT_WIDTH * 0.16,
            CONTENT_WIDTH * 0.20,
            CONTENT_WIDTH * 0.18,
        ],
        styles,
    )
    return _section("Evidence / provenance", table, styles)


def _limitations_section(payload: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    confidence = payload.get("confidence") or {}
    limitations = payload.get("limitations") or []
    flowables: list[Any] = [Paragraph("Confidence / limitations", styles["section"])]
    confidence_heading = Paragraph("Recorded confidence", styles["subsection"])
    if not confidence:
        flowables.append(confidence_heading)
        flowables.append(_empty_state(styles))
    else:
        flowables.append(confidence_heading)
        flowables.append(
            _kv_table(
                [(str(key), value) for key, value in confidence.items()],
                styles,
            )
        )
    limitations_heading = Paragraph("Limitations", styles["subsection"])
    if not limitations:
        flowables.append(limitations_heading)
        flowables.append(_empty_state(styles))
    else:
        items = [
            ListItem(Paragraph(escape(_display(note)), styles["limit"]), leftIndent=8)
            for note in limitations
        ]
        flowables.append(limitations_heading)
        flowables.append(
            ListFlowable(
                items,
                bulletType="bullet",
                start="•",
                leftIndent=12,
                bulletFontName="Helvetica",
                bulletFontSize=8,
                spaceBefore=0,
                spaceAfter=0,
            )
        )
    return [KeepTogether(flowables)]


def render_investigation_report_pdf(payload: dict[str, Any]) -> bytes:
    """Render the assembled report payload as an A4 Platypus PDF."""
    styles = _styles()
    investigation = payload.get("investigation") or {}
    report_name = str(investigation.get("name") or "CNAS Investigation Report")
    generated_at = _display(payload.get("generated_at"))

    story: list[Any] = []
    story.extend(_title_block(payload, styles))
    story.append(Spacer(1, 8))
    story.extend(_investigation_section(payload, styles))
    story.extend(_cases_section(payload, styles))
    story.extend(_people_section(payload, styles))
    story.extend(_network_section(payload, styles))
    story.extend(_analytics_section(payload, styles))
    story.extend(_an2_section(payload, styles))
    story.extend(_adjudication_section(payload, styles))
    story.extend(_evidence_section(payload, styles))
    story.extend(_limitations_section(payload, styles))

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=LEFT_MARGIN,
        rightMargin=RIGHT_MARGIN,
        topMargin=TOP_MARGIN,
        bottomMargin=BOTTOM_MARGIN,
        title="CNAS INVESTIGATION REPORT",
        author="CNAS",
        pageCompression=0,
    )

    def on_page(canvas, doc) -> None:
        _draw_chrome(
            canvas,
            doc,
            report_name=report_name,
            generated_at=generated_at,
        )

    document.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buffer.getvalue()
