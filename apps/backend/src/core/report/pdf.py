"""PDF report generation for an Analysis.

Produces a Lexitor-branded PDF with:
- Cover page (filename, datum, summary counts)
- Summary table (rb, status, broj nalaza)
- Per-stavka sections (kontekst + Lexitor finding + user verdict + comment)

Built on ReportLab (pure Python — no native deps, works on Windows out
of the box). Croatian diacritics rendered via Arial registered from the
Windows system fonts directory; falls back to Helvetica if Arial isn't
available."""

from __future__ import annotations

import io
import os
from datetime import datetime
from typing import Any, Iterable

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from src.models import Analysis, AnalysisItem, AnalysisItemStatus, Project

# ---------------------------------------------------------------------------
# Brand palette (mirrors apps/web Tailwind tokens)
INK = colors.HexColor("#0B1320")
NAVY = colors.HexColor("#1A2332")
SURFACE = colors.HexColor("#FAFAF8")
SURFACE_2 = colors.HexColor("#F2F0E9")
BRAND_BORDER = colors.HexColor("#E5E2D7")
MUTED = colors.HexColor("#7B7363")
SIGNAL = colors.HexColor("#3B82C4")
GOLD = colors.HexColor("#B8893E")

STATUS_COLORS: dict[AnalysisItemStatus, colors.Color] = {
    AnalysisItemStatus.OK: colors.HexColor("#3F7D45"),
    AnalysisItemStatus.WARN: colors.HexColor("#A87F2E"),
    AnalysisItemStatus.FAIL: colors.HexColor("#A8392B"),
    AnalysisItemStatus.UNCERTAIN: colors.HexColor("#6B4A8E"),
    AnalysisItemStatus.ACCEPTED: colors.HexColor("#2A6DB0"),
    AnalysisItemStatus.NEUTRAL: colors.HexColor("#7B7363"),
}

STATUS_LABELS: dict[AnalysisItemStatus, str] = {
    AnalysisItemStatus.OK: "Usklađeno",
    AnalysisItemStatus.WARN: "Upozorenje",
    AnalysisItemStatus.FAIL: "Kršenje",
    AnalysisItemStatus.UNCERTAIN: "Pravna nesigurnost",
    AnalysisItemStatus.ACCEPTED: "Prihvaćen rizik",
    AnalysisItemStatus.NEUTRAL: "Nije provjereno",
}


# ---------------------------------------------------------------------------
# Font registration

_FONT_REGULAR = "Helvetica"  # default; replaced if Arial registers
_FONT_BOLD = "Helvetica-Bold"


def _register_fonts() -> None:
    """Register Arial from the Windows fonts dir for Croatian diacritics.
    Falls back to Helvetica when not available (renders čćžšđ via
    standard Latin Extended via WinAnsiEncoding's CP1252 — which
    actually misses č/ć for Helvetica). Best to find Arial."""
    global _FONT_REGULAR, _FONT_BOLD
    candidates_regular = [
        ("Arial", r"C:\Windows\Fonts\arial.ttf"),
        ("Arial", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    candidates_bold = [
        ("Arial-Bold", r"C:\Windows\Fonts\arialbd.ttf"),
        ("Arial-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]
    for name, path in candidates_regular:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                _FONT_REGULAR = name
                break
            except Exception:
                continue
    for name, path in candidates_bold:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                _FONT_BOLD = name
                break
            except Exception:
                continue


_register_fonts()


# ---------------------------------------------------------------------------
# Paragraph styles

def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()["Normal"]
    return {
        "h1": ParagraphStyle(
            "h1",
            parent=base,
            fontName=_FONT_BOLD,
            fontSize=22,
            leading=28,
            textColor=INK,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base,
            fontName=_FONT_BOLD,
            fontSize=14,
            leading=18,
            textColor=INK,
            spaceBefore=12,
            spaceAfter=6,
        ),
        "h3": ParagraphStyle(
            "h3",
            parent=base,
            fontName=_FONT_BOLD,
            fontSize=11,
            leading=14,
            textColor=NAVY,
            spaceBefore=6,
            spaceAfter=3,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base,
            fontName=_FONT_REGULAR,
            fontSize=10,
            leading=14,
            textColor=NAVY,
        ),
        "muted": ParagraphStyle(
            "muted",
            parent=base,
            fontName=_FONT_REGULAR,
            fontSize=9,
            leading=12,
            textColor=MUTED,
        ),
        "label": ParagraphStyle(
            "label",
            parent=base,
            fontName=_FONT_BOLD,
            fontSize=8,
            leading=10,
            textColor=MUTED,
            spaceAfter=2,
        ),
        "kbd": ParagraphStyle(
            "kbd",
            parent=base,
            fontName=_FONT_REGULAR,
            fontSize=9,
            leading=12,
            textColor=NAVY,
        ),
    }


# ---------------------------------------------------------------------------
# Page template (header + footer)

def _on_page(canvas, doc) -> None:  # type: ignore[no-untyped-def]
    canvas.saveState()
    # Footer
    canvas.setFont(_FONT_REGULAR, 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(20 * mm, 12 * mm, "Lexitor — analiza javne nabave")
    canvas.drawRightString(
        A4[0] - 20 * mm, 12 * mm, f"Stranica {canvas.getPageNumber()}"
    )
    # Top accent bar
    canvas.setFillColor(GOLD)
    canvas.rect(20 * mm, A4[1] - 14 * mm, 12 * mm, 1.2, fill=1, stroke=0)
    canvas.restoreState()


def _draw_lexitor_wordmark(canvas, x: float, y: float, height: float = 10 * mm) -> None:
    """Render the Lexitor wordmark inline on the canvas — bold serif text
    with a gold underline accent. Used in lieu of a logo file so the
    report stays self-contained (no external assets to ship)."""
    canvas.saveState()
    text = "Lexitor"
    canvas.setFillColor(INK)
    canvas.setFont(_FONT_BOLD, height * 0.72)
    canvas.drawString(x, y, text)
    width = pdfmetrics.stringWidth(text, _FONT_BOLD, height * 0.72)
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(1.4)
    canvas.line(x, y - 1.6, x + width, y - 1.6)
    canvas.restoreState()


def _company_logo_flowable(project: Project | None, max_height: float = 12 * mm) -> Any:
    """Try to load the company logo as a flowable Image. Falls back to
    a Paragraph rendering the project name when no logo file is set
    or the file isn't readable."""
    styles = _styles()
    name_style = ParagraphStyle(
        "company_name",
        parent=styles["body"],
        fontName=_FONT_BOLD,
        fontSize=12,
        textColor=NAVY,
        alignment=2,  # right
    )
    if project is None:
        return Paragraph("", name_style)

    logo_path = project.logo_path
    if logo_path and os.path.exists(logo_path):
        try:
            img = Image(logo_path)
            scale = max_height / float(img.imageHeight)
            img._restrictSize(60 * mm, max_height)
            img.drawHeight = max_height
            img.drawWidth = float(img.imageWidth) * scale
            img.hAlign = "RIGHT"
            return img
        except Exception:
            pass
    # Fallback: render project name as text
    return Paragraph(project.name or "", name_style)


# ---------------------------------------------------------------------------
# Helpers

def _safe(text: Any) -> str:
    """ReportLab Paragraph parses HTML-like markup, so we escape user
    text to avoid `&`/`<`/`>` breaking the layout."""
    if text is None:
        return ""
    s = str(text)
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _format_eur(value: Any) -> str:
    if value is None or value == "":
        return "—"
    try:
        n = float(value)
    except (TypeError, ValueError):
        return _safe(value)
    return f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"


def _format_date(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    return dt.strftime("%d.%m.%Y. %H:%M")


def _status_pill(status: AnalysisItemStatus) -> Table:
    """Small coloured pill representing item status."""
    color = STATUS_COLORS.get(status, MUTED)
    label = STATUS_LABELS.get(status, status.value)
    cell = Table(
        [[label]],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), color),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                ("FONT", (0, 0), (-1, -1), _FONT_BOLD, 8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("ROUNDEDCORNERS", [3, 3, 3, 3]),
            ]
        ),
    )
    return cell


# ---------------------------------------------------------------------------
# Cover page


def _logo_header_table(project: Project | None) -> Table:
    """Top-of-cover band: Lexitor wordmark (left) | Company logo (right).
    Drawn via flowables so the inline canvas helpers handle font
    fallbacks and we don't reach for an external SVG asset."""
    # Lexitor side: wordmark + tagline
    lex_table = Table(
        [
            [Paragraph(
                f"<font name='{_FONT_BOLD}' size='22' color='#0B1320'>Lexitor</font>",
                ParagraphStyle("lex", fontName=_FONT_BOLD, fontSize=22, leading=24, textColor=INK),
            )],
            [Paragraph(
                "<font color='#7B7363'>AI asistent javne nabave</font>",
                ParagraphStyle("lex_tag", fontName=_FONT_REGULAR, fontSize=8, leading=10, textColor=MUTED),
            )],
        ],
        colWidths=[80 * mm],
        style=TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, 0), 1.4, GOLD),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (0, 0), 4),
                ("TOPPADDING", (0, 1), (0, 1), 2),
            ]
        ),
    )
    company_flowable = _company_logo_flowable(project, max_height=14 * mm)
    return Table(
        [[lex_table, company_flowable]],
        colWidths=[90 * mm, 80 * mm],
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        ),
    )


def _cover_story(
    *,
    document_filename: str,
    analysed_at: datetime | None,
    summary: dict[str, Any] | None,
    item_count: int,
    only_errors: bool,
    project: Project | None,
) -> list:
    styles = _styles()
    parts: list = []
    parts.append(_logo_header_table(project))
    parts.append(Spacer(1, 24 * mm))
    parts.append(Paragraph("Izvještaj analize", styles["h1"]))
    parts.append(Spacer(1, 4 * mm))
    parts.append(Paragraph(_safe(document_filename), styles["h2"]))
    parts.append(Spacer(1, 12 * mm))

    info_rows = [
        ["Analiza završena", _format_date(analysed_at)],
        ["Stavki ukupno", str(item_count)],
        ["Filter", "Samo greške" if only_errors else "Sve stavke"],
    ]
    if summary:
        for label_key, label, color_status in (
            ("ok", "Usklađeno", AnalysisItemStatus.OK),
            ("warn", "Upozorenje", AnalysisItemStatus.WARN),
            ("fail", "Kršenje", AnalysisItemStatus.FAIL),
        ):
            count = summary.get(label_key, 0)
            info_rows.append([label, str(count)])

    info = Table(
        info_rows,
        colWidths=[60 * mm, 90 * mm],
        style=TableStyle(
            [
                ("FONT", (0, 0), (0, -1), _FONT_BOLD, 9),
                ("FONT", (1, 0), (1, -1), _FONT_REGULAR, 9),
                ("TEXTCOLOR", (0, 0), (0, -1), MUTED),
                ("TEXTCOLOR", (1, 0), (1, -1), NAVY),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, -2), 0.4, BRAND_BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ]
        ),
    )
    parts.append(info)
    parts.append(Spacer(1, 30 * mm))
    parts.append(
        Paragraph(
            "Generirano automatski iz Lexitor analize. Izvještaj sadrži "
            "stavke s pripadnim Lexitor nalazima, povratnim informacijama "
            "korisnika i citatima ZJN-a gdje su primjenjivi.",
            styles["muted"],
        )
    )
    parts.append(PageBreak())
    return parts


# ---------------------------------------------------------------------------
# Per-item section


def _verdict_label(verdict: Any) -> tuple[str, colors.Color]:
    if verdict == "correct":
        return "Korisnik: ✓ Točno", STATUS_COLORS[AnalysisItemStatus.OK]
    if verdict == "incorrect":
        return "Korisnik: ✗ Pogrešno", STATUS_COLORS[AnalysisItemStatus.FAIL]
    return "", MUTED


def _cell_paragraph(text: Any, *, align: str = "LEFT", muted: bool = False) -> Paragraph:
    """Wrap cell content in a Paragraph so text wraps inside the column
    instead of overflowing into the next one."""
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    align_map = {"LEFT": TA_LEFT, "RIGHT": TA_RIGHT, "CENTER": TA_CENTER}
    style = ParagraphStyle(
        "cell",
        fontName=_FONT_REGULAR,
        fontSize=8.5,
        leading=11,
        textColor=MUTED if muted else NAVY,
        alignment=align_map.get(align, TA_LEFT),
        wordWrap="CJK",  # enables wrap on long unbroken Croatian words
    )
    return Paragraph(_safe(text) if text not in (None, "") else "—", style)


def _math_table(math_rows: list[dict[str, Any]]) -> Table | None:
    if not math_rows:
        return None
    has_excel_row = any(mr.get("row") is not None for mr in math_rows)
    has_position = any(mr.get("position_label") for mr in math_rows)

    headers = []
    if has_excel_row:
        headers.append("Red")
    headers += ["Podstavka", "Jed. mjere", "Količina", "Jed. cijena", "Iznos"]

    rows: list[list[Any]] = [headers]
    for mr in math_rows:
        row: list[Any] = []
        if has_excel_row:
            row.append(_cell_paragraph(mr.get("row") or "", align="RIGHT"))
        row.append(
            _cell_paragraph(
                mr.get("position_label") if has_position else mr.get("position_label") or ""
            )
        )
        row.append(_cell_paragraph(mr.get("jm") or "—", align="LEFT"))
        kol_val = mr.get("kol")
        row.append(
            _cell_paragraph(
                kol_val if kol_val not in (None, "") else "—",
                align="RIGHT",
            )
        )
        row.append(_cell_paragraph(_format_eur(mr.get("cijena")), align="RIGHT"))
        row.append(
            _cell_paragraph(
                _format_eur(
                    mr.get("iznos") if mr.get("iznos") not in (None, "") else mr.get("computed_iznos")
                ),
                align="RIGHT",
            )
        )
        rows.append(row)

    # Wider Podstavka column, slightly narrower right-side money columns
    # so long descriptions like "FID strujna zaštitna sklopka 4p, 25/0,03 A"
    # wrap inside their cell instead of overflowing into "Jed. mjere".
    # Total ≤ 170mm (page width 210mm minus 2×20mm margins).
    col_widths = [10 * mm] if has_excel_row else []
    col_widths += [72 * mm, 16 * mm, 22 * mm, 22 * mm, 28 * mm]

    style_cmds = [
        ("FONT", (0, 0), (-1, 0), _FONT_BOLD, 7),
        ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
        ("BACKGROUND", (0, 0), (-1, 0), SURFACE_2),
        ("ALIGN", (-3, 0), (-1, 0), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("LINEABOVE", (0, 1), (-1, -1), 0.3, BRAND_BORDER),
    ]
    if has_excel_row:
        style_cmds.append(("ALIGN", (0, 0), (0, 0), "RIGHT"))

    return Table(rows, colWidths=col_widths, style=TableStyle(style_cmds), hAlign="LEFT")


def _item_story(item: AnalysisItem, styles: dict[str, ParagraphStyle]) -> list:
    """Render one item as a flowable group. Wrapped in KeepTogether so
    short items don't break across pages."""
    parts: list = []

    # Header: rb + status pill
    meta = item.metadata_json or {}
    rb = meta.get("rb") or ""
    sheet = meta.get("sheet") or ""
    title = meta.get("title") or ""

    header_left_parts: list[str] = []
    if sheet:
        header_left_parts.append(f"<font color='#7B7363'>{_safe(sheet)}</font>")
    if rb:
        header_left_parts.append(f"<b>{_safe(rb)}</b>")
    header_left = " · ".join(header_left_parts) or _safe(item.label or "")

    header_table = Table(
        [[Paragraph(header_left, styles["body"]), _status_pill(item.status)]],
        colWidths=[140 * mm, 30 * mm],
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        ),
    )
    parts.append(header_table)

    if title:
        parts.append(Paragraph(_safe(title), styles["h3"]))

    # Body text
    if item.text:
        for line in str(item.text).splitlines():
            line = line.strip()
            if line:
                parts.append(Paragraph(_safe(line), styles["body"]))

    # Math rows
    math_rows = (meta.get("math_rows") or []) if isinstance(meta, dict) else []
    table = _math_table(math_rows)
    if table is not None:
        parts.append(Spacer(1, 3 * mm))
        parts.append(table)

    # Lexitor finding
    if item.explanation or item.suggestion:
        parts.append(Spacer(1, 3 * mm))
        parts.append(Paragraph("Lexitor analiza", styles["label"]))
        accent = STATUS_COLORS.get(item.status, MUTED)
        accent_hex = "#{:02X}{:02X}{:02X}".format(
            int(accent.red * 255), int(accent.green * 255), int(accent.blue * 255)
        )
        if item.explanation:
            # Strip the <<DEMO>> marker from random mock findings
            text = str(item.explanation)
            if text.startswith("<<DEMO>>"):
                text = text[len("<<DEMO>>"):].strip()
            parts.append(
                Paragraph(
                    f"<font color='{accent_hex}'><b>Zašto:</b></font> {_safe(text)}",
                    styles["body"],
                )
            )
        if item.suggestion:
            parts.append(
                Paragraph(
                    f"<font color='{accent_hex}'><b>Predloženi ispravak:</b></font> {_safe(item.suggestion)}",
                    styles["body"],
                )
            )

    # Citations
    if item.citations:
        cites = "; ".join(
            f"{c.source.value.upper()} {_safe(c.reference)}" for c in item.citations
        )
        parts.append(Paragraph(cites, styles["muted"]))

    # User feedback
    if item.user_verdict or item.user_comment:
        verdict_label, verdict_color = _verdict_label(
            item.user_verdict.value if item.user_verdict else None
        )
        verdict_hex = "#{:02X}{:02X}{:02X}".format(
            int(verdict_color.red * 255),
            int(verdict_color.green * 255),
            int(verdict_color.blue * 255),
        )
        parts.append(Spacer(1, 2 * mm))
        if verdict_label:
            parts.append(
                Paragraph(
                    f"<font color='{verdict_hex}'><b>{_safe(verdict_label)}</b></font>",
                    styles["body"],
                )
            )
        if item.user_comment:
            parts.append(
                Paragraph(
                    f"„{_safe(item.user_comment)}”",
                    styles["body"],
                )
            )

    parts.append(Spacer(1, 8 * mm))
    parts.append(
        Table(
            [[""]],
            colWidths=[170 * mm],
            style=TableStyle(
                [("LINEBELOW", (0, 0), (-1, -1), 0.3, BRAND_BORDER)]
            ),
        )
    )
    parts.append(Spacer(1, 4 * mm))

    return [KeepTogether(parts)]


# ---------------------------------------------------------------------------
# Summary table


def _summary_table(items: Iterable[AnalysisItem], styles: dict[str, ParagraphStyle]) -> list:
    parts: list = [Paragraph("Sažetak", styles["h2"])]
    rows: list[list[Any]] = [
        [
            _cell_paragraph("Sheet"),
            _cell_paragraph("RB"),
            _cell_paragraph("Naslov"),
            _cell_paragraph("Status"),
            _cell_paragraph("Korisnik"),
        ]
    ]
    for it in items:
        meta = it.metadata_json or {}
        sheet = meta.get("sheet") or ""
        rb = meta.get("rb") or ""
        title = meta.get("title") or it.label or ""
        rows.append([
            _cell_paragraph(sheet),
            _cell_paragraph(rb),
            _cell_paragraph(title),
            _cell_paragraph(STATUS_LABELS.get(it.status, it.status.value)),
            _cell_paragraph(
                "Točno"
                if (it.user_verdict and it.user_verdict.value == "correct")
                else "Pogrešno"
                if (it.user_verdict and it.user_verdict.value == "incorrect")
                else ""
            ),
        ])
    table = Table(
        rows,
        colWidths=[36 * mm, 14 * mm, 72 * mm, 30 * mm, 18 * mm],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), SURFACE_2),
                ("LINEBELOW", (0, 0), (-1, -1), 0.3, BRAND_BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        ),
        hAlign="LEFT",
        repeatRows=1,
    )
    parts.append(table)
    parts.append(PageBreak())
    return parts


# ---------------------------------------------------------------------------
# Public API


def build_analysis_pdf(
    *,
    analysis: Analysis,
    items: list[AnalysisItem],
    document_filename: str,
    only_errors: bool = False,
    project: Project | None = None,
) -> bytes:
    """Render `analysis` and `items` into a Lexitor-branded PDF, returning
    the raw bytes. Caller is responsible for setting the response
    Content-Disposition / filename.

    `only_errors=True` filters to items whose status is FAIL/WARN/
    UNCERTAIN. Items with `include_in_pdf=False` are always excluded
    regardless of filter (per-item user toggle).

    `project` controls the company logo on the cover page — if it has a
    `logo_path` pointing at a readable image, that image renders at the
    top-right; otherwise the project name renders as text.
    """
    error_statuses = {
        AnalysisItemStatus.FAIL,
        AnalysisItemStatus.WARN,
        AnalysisItemStatus.UNCERTAIN,
    }
    visible_items = [
        it
        for it in items
        if it.include_in_pdf
        and (not only_errors or it.status in error_statuses)
    ]

    buf = io.BytesIO()
    doc = BaseDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=18 * mm,
        title=f"Lexitor — {document_filename}",
        author="Lexitor",
    )
    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
        id="main",
    )
    doc.addPageTemplates(
        [PageTemplate(id="default", frames=[frame], onPage=_on_page)]
    )

    styles = _styles()
    story: list = []
    story += _cover_story(
        document_filename=document_filename,
        analysed_at=analysis.updated_at,
        summary=analysis.summary,
        item_count=len(visible_items),
        only_errors=only_errors,
        project=project,
    )
    story += _summary_table(visible_items, styles)

    story.append(Paragraph("Stavke", styles["h2"]))
    for it in visible_items:
        story += _item_story(it, styles)

    if not visible_items:
        story.append(
            Paragraph(
                "Nema stavki koje zadovoljavaju kriterij filtra.",
                styles["muted"],
            )
        )

    doc.build(story)
    return buf.getvalue()
