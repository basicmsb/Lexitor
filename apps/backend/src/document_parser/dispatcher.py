from __future__ import annotations

from pathlib import Path

from src.document_parser.arhigon_parser import parse_arhigon
from src.document_parser.base import ParsedDocument, ParserError
from src.document_parser.pdf_parser import parse_pdf
from src.document_parser.xlsx_parser import parse_xlsx

SUPPORTED_EXTENSIONS = {".pdf", ".xlsx", ".arhigonfile"}


def supported_extensions() -> set[str]:
    return SUPPORTED_EXTENSIONS


def parse_document(path: Path) -> ParsedDocument:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return parse_pdf(path)
    if suffix == ".xlsx":
        return parse_xlsx(path)
    if suffix == ".arhigonfile":
        return parse_arhigon(path)
    raise ParserError(f"Nepodržani format: {suffix}")
