from __future__ import annotations

from pathlib import Path

from src.document_parser.arhigon_parser import parse_arhigon
from src.document_parser.base import ParsedDocument, ParserError
from src.document_parser.canonical_xlsx import parse_canonical_xlsx
from src.document_parser.pdf_parser import parse_pdf

SUPPORTED_EXTENSIONS = {".pdf", ".xlsx", ".xls", ".arhigonfile", ".arhigon"}


def supported_extensions() -> set[str]:
    return SUPPORTED_EXTENSIONS


def parse_document(path: Path) -> ParsedDocument:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return parse_pdf(path)
    if suffix in (".xlsx", ".xls"):
        return parse_canonical_xlsx(path)
    if suffix in (".arhigonfile", ".arhigon"):
        return parse_arhigon(path)
    raise ParserError(f"Nepodržani format: {suffix}")
