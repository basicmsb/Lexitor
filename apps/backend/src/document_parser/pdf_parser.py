"""PDF parser za DON dokumente.

Ekstrahira tekst svake stranice, deduplicira ponavljajuća zaglavlja/footere
(koji se pojavljuju na svakoj stranici PDF-a), i prosljeđuje konačan tekst
kroz DON markdown_parser radi klasifikacije blokova (kind, rb, chapter_path).

Time PDF dokumenti imaju **istu strukturalnu analizu kao .md i .docx** —
section_header / paragraph / requirement / criterion / deadline / list / table.
"""
from __future__ import annotations

import logging
import re
from collections import Counter
from pathlib import Path

import pdfplumber

from src.document_parser.base import ParsedDocument, ParserError

logger = logging.getLogger(__name__)


def _extract_page_text(page) -> str:
    """Ekstrahira tekst stranice. Pdfplumber daje extract_text() koji čuva
    layout (linije razdvojene s \\n)."""
    try:
        return page.extract_text() or ""
    except Exception:  # noqa: BLE001
        return ""


def _identify_repeating_lines(pages_text: list[str], min_pages: int = 3) -> set[str]:
    """Identificira linije koje se ponavljaju na **najmanje** `min_pages`
    stranica — vjerojatno zaglavlja, footeri, paginacija ("str. N", brojevi
    stranica). Vraća set linija (lowercase, stripped) za filtriranje.

    Heuristika:
    - Linija se računa kao "ponavljajuća" ako se pojavi na ≥min_pages stranica
    - "str. 12" / "str. 13" / "str. N" patterni se hvataju zasebno (regex)
    """
    # Skupi sve linije po stranicama (samo neprazne, kraće od 200 char-a —
    # dugačke su content, ne header)
    line_pages: dict[str, set[int]] = {}
    for page_idx, text in enumerate(pages_text):
        seen_on_page: set[str] = set()
        for line in text.split("\n"):
            normalized = line.strip()
            if not normalized or len(normalized) > 200:
                continue
            # Normalize: lowercase + collapse whitespace
            key = re.sub(r"\s+", " ", normalized.lower())
            if key in seen_on_page:
                continue
            seen_on_page.add(key)
            line_pages.setdefault(key, set()).add(page_idx)

    # Linija je "ponavljajuća" ako se pojavila na ≥min_pages
    return {key for key, pages in line_pages.items() if len(pages) >= min_pages}


# Patterni paginacije koji uvijek idu out (regardless od ponavljanja)
_PAGINATION_PATTERNS = [
    re.compile(r"^str\.\s*\d+$", re.IGNORECASE),
    re.compile(r"^stranica\s*\d+(\s*/\s*\d+)?$", re.IGNORECASE),
    re.compile(r"^\d+$"),  # broj sam
    re.compile(r"^\d+\s*/\s*\d+$"),  # "5 / 23"
    re.compile(r"^page\s+\d+", re.IGNORECASE),
]


def _is_pagination_line(line: str) -> bool:
    s = line.strip()
    return any(p.match(s) for p in _PAGINATION_PATTERNS)


def _clean_page_text(text: str, repeating: set[str]) -> str:
    """Filtriraj ponavljajuće linije i paginaciju iz teksta stranice."""
    kept: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            kept.append("")  # zadrži prazne linije za blokove
            continue
        if _is_pagination_line(stripped):
            continue
        normalized = re.sub(r"\s+", " ", stripped.lower())
        if normalized in repeating:
            continue
        kept.append(line)
    # Collapse multiple empty lines u single
    result_lines: list[str] = []
    prev_empty = False
    for line in kept:
        is_empty = not line.strip()
        if is_empty and prev_empty:
            continue
        result_lines.append(line)
        prev_empty = is_empty
    return "\n".join(result_lines).strip()


def parse_pdf(path: Path) -> ParsedDocument:
    """Parsa PDF s deduplikacijom zaglavlja + prosljedom kroz DON tekst parser.

    Pipeline:
    1. pdfplumber ekstrahira tekst svake stranice
    2. Identificira linije koje se ponavljaju na 3+ stranica → header/footer
    3. Filtrira te linije + paginaciju ("str. N", samo broj)
    4. Spaja sve stranice u jedan tekst (separator: 2× newline za paragraph boundary)
    5. Šalje kroz `parse_text` (isti kao za .md/.docx) — DON klasifikacija
    """
    try:
        with pdfplumber.open(str(path)) as pdf:
            page_count = len(pdf.pages)
            pages_text = [_extract_page_text(p) for p in pdf.pages]
    except Exception as exc:
        raise ParserError(f"PDF parsing nije uspio: {exc}") from exc

    if not any(pages_text):
        raise ParserError(
            "PDF ne sadrži ekstraktabilan tekst — vjerojatno je skeniran. "
            "Konvertiraj u tekst (OCR) ili spremi kao .docx."
        )

    # Detect repeating header/footer lines (≥3 stranica)
    min_pages_for_repeat = max(3, page_count // 4)
    repeating = _identify_repeating_lines(pages_text, min_pages=min_pages_for_repeat)
    logger.info(
        "PDF parser: %d strana, %d ponavljajućih linija (header/footer) filtrirano",
        page_count, len(repeating),
    )

    # Spoji clean tekst svih stranica
    cleaned_pages = [_clean_page_text(t, repeating) for t in pages_text]
    full_text = "\n\n".join(p for p in cleaned_pages if p)

    if not full_text.strip():
        raise ParserError(
            "PDF nakon uklanjanja zaglavlja nije ostavio sadržaj. "
            "Vjerojatno je dokument samo zaglavlje/footer šablona."
        )

    # Proslijedi kroz DON tekst parser
    from src.document_parser.markdown_parser import parse_text
    parsed = parse_text(full_text, source_format="pdf", filename=path.name)

    # Dodaj page_count u metadata
    parsed.metadata["page_count"] = page_count
    parsed.metadata["repeating_lines_filtered"] = len(repeating)
    return parsed
