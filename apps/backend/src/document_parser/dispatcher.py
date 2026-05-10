from __future__ import annotations

from pathlib import Path

from src.document_parser.arhigon_parser import parse_arhigon
from src.document_parser.base import ParsedDocument, ParserError
from src.document_parser.canonical_xlsx import parse_canonical_xlsx
from src.document_parser.pdf_parser import parse_pdf

SUPPORTED_EXTENSIONS = {
    ".pdf", ".xlsx", ".xls", ".arhigonfile", ".arhigon",
    ".md", ".txt", ".docx", ".doc",
}


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
    if suffix in (".md", ".txt"):
        # DON tekst parser radi za oba: pravi markdown (.md s # markerima)
        # i plain tekst (.txt nakon copy-paste s EOJN viewer-a)
        from src.document_parser.markdown_parser import parse_markdown
        return parse_markdown(path)
    if suffix == ".docx":
        from src.document_parser.docx_parser import parse_docx
        return parse_docx(path)
    if suffix == ".doc":
        # Stari binary Word format — python-docx ne podržava. Korisnik
        # neka konvertira u .docx (Word "Save As") ili .pdf.
        raise ParserError(
            "Format „.doc” (stari Word binary) nije podržan. "
            "Otvori u Wordu i spremi kao „.docx” ili „.pdf”."
        )
    raise ParserError(f"Nepodržani format: {suffix}")
