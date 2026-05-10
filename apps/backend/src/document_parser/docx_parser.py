"""DON .docx parser — koristi `python-docx` da iz Word dokumenta izvuče
strukturu (naslovi po stilu, paragrafi, liste, tablice) i pretvori je u
markdown-like tekst, pa preda nakon toga DON markdown parseru.

Strategija:
- Heading 1/2/3/… → `# ` / `## ` / `### ` / …
- List bullet/numbered → `- ` prefix (parser će prepoznati kao list)
- Tablice → markdown pipe sintaksa (parser će klasificirati kao 'table')
- Obični paragrafi → kao plain text, parser radi remainder.

Time se reusa cijela DON-markdown-pipeline (klasifikacija blokova,
chapter_path, rb extraction) bez duplikata logike.
"""
from __future__ import annotations

from pathlib import Path

from src.document_parser.base import ParsedDocument, ParserError
from src.document_parser.markdown_parser import parse_text


def _heading_level(style_name: str) -> int | None:
    """Vrati depth (1-6) ako je paragraph style 'Heading N' / 'Naslov N',
    inače None.

    python-docx vraća localized ili English style ime ovisno o template-u.
    Pokrivamo oba."""
    if not style_name:
        return None
    s = style_name.strip().lower()
    # English: "Heading 1", "Heading 2", ...
    if s.startswith("heading "):
        try:
            n = int(s.split()[1])
            if 1 <= n <= 6:
                return n
        except (ValueError, IndexError):
            return None
    # Hrvatski: "Naslov 1", "Naslov 2", ...
    if s.startswith("naslov "):
        try:
            n = int(s.split()[1])
            if 1 <= n <= 6:
                return n
        except (ValueError, IndexError):
            return None
    # Title style → najviši naslov
    if s in ("title", "naslov", "naslov knjige", "book title"):
        return 1
    return None


def _is_list_paragraph(paragraph) -> bool:
    """Heuristika: paragraph je dio liste ako mu style sadrži 'List' /
    'Lista' ili numeracija u XML-u.

    python-docx ne izlaže direktan list-status, ali stil i numId hint-aju."""
    style = (paragraph.style.name or "").lower()
    if "list" in style or "lista" in style or "bullet" in style:
        return True
    # Provjeri ima li paragraph numPr (numbering properties) u XML-u
    pPr = paragraph._p.pPr
    if pPr is not None and pPr.numPr is not None:
        return True
    return False


def _table_to_markdown(table) -> str:
    """Pretvori docx tablicu u markdown pipe-tablicu. Empty cells → ' '."""
    rows: list[str] = []
    for row in table.rows:
        cells = [
            (cell.text or "").strip().replace("\n", " ").replace("|", "/")
            for cell in row.cells
        ]
        rows.append("| " + " | ".join(cells) + " |")
    if not rows:
        return ""
    # Insert markdown separator row after first row
    if len(rows) >= 1:
        n_cols = rows[0].count("|") - 1
        separator = "| " + " | ".join(["---"] * n_cols) + " |"
        rows.insert(1, separator)
    return "\n".join(rows)


def parse_docx(path: Path) -> ParsedDocument:
    """Pročitaj .docx i pretvori u markdown-like tekst, pa parsiraj
    standardnim DON markdown parserom."""
    try:
        from docx import Document
        from docx.document import Document as _DocDocument
        from docx.oxml.table import CT_Tbl
        from docx.oxml.text.paragraph import CT_P
        from docx.table import Table
        from docx.text.paragraph import Paragraph
    except ImportError as exc:
        raise ParserError(
            "python-docx nije instaliran — `pip install python-docx`"
        ) from exc

    try:
        doc = Document(str(path))
    except Exception as exc:  # noqa: BLE001
        raise ParserError(f"Ne mogu otvoriti {path.name}: {exc}") from exc

    # Walk-aj sve elemente body-ja u redoslijedu — paragrafi i tablice
    # interpoliraju se, treba ih obraditi redom pojavljivanja.
    lines: list[str] = []
    body = doc.element.body
    for child in body.iterchildren():
        if isinstance(child, CT_P):
            paragraph = Paragraph(child, doc)
            text = (paragraph.text or "").strip()
            if not text:
                lines.append("")
                continue
            level = _heading_level(paragraph.style.name)
            if level:
                lines.append("#" * level + " " + text)
                lines.append("")
                continue
            if _is_list_paragraph(paragraph):
                lines.append(f"- {text}")
                continue
            lines.append(text)
            lines.append("")
        elif isinstance(child, CT_Tbl):
            table = Table(child, doc)
            md = _table_to_markdown(table)
            if md:
                lines.append("")
                lines.append(md)
                lines.append("")
        # Ignore other elements (sectPr itd.)

    converted = "\n".join(lines)
    parsed = parse_text(
        converted,
        source_format="docx",
        filename=path.name,
    )
    return parsed
