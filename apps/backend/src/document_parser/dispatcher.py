from __future__ import annotations

from pathlib import Path

from src.document_parser.arhigon_parser import parse_arhigon
from src.document_parser.base import ParsedDocument, ParserError
from src.document_parser.canonical_xlsx import parse_canonical_xlsx
from src.document_parser.pdf_parser import parse_pdf
from src.document_parser.subtype import detect_subtype_from_filename

SUPPORTED_EXTENSIONS = {
    ".pdf", ".xlsx", ".xls", ".arhigonfile", ".arhigon",
    ".md", ".txt", ".docx", ".doc",
}


def supported_extensions() -> set[str]:
    return SUPPORTED_EXTENSIONS


def _inject_subtype(parsed: ParsedDocument, filename: str) -> ParsedDocument:
    """Detect i ubaci document_subtype u parsed.metadata + svaki ParsedItem."""
    subtype = detect_subtype_from_filename(filename)
    parsed.metadata["document_subtype"] = subtype
    parsed.metadata["filename_for_subtype"] = filename
    if subtype:
        for item in parsed.items:
            item.metadata.setdefault("document_subtype", subtype)
    return parsed


def parse_document(path: Path, *, filename_override: str | None = None) -> ParsedDocument:
    """Parse dokumenta + detekcija document_subtype-a iz filename-a.

    `filename_override` se koristi kad je file spremljen pod random UUID
    naziva (npr. uploaded/abc-def.pdf) ali stvarno ime je drugo (Document.filename).
    """
    suffix = path.suffix.lower()
    name_for_subtype = filename_override or path.name

    if suffix == ".pdf":
        parsed = parse_pdf(path)
    elif suffix in (".xlsx", ".xls"):
        parsed = parse_canonical_xlsx(path)
    elif suffix in (".arhigonfile", ".arhigon"):
        parsed = parse_arhigon(path)
    elif suffix in (".md", ".txt"):
        from src.document_parser.markdown_parser import parse_markdown
        parsed = parse_markdown(path)
    elif suffix == ".docx":
        from src.document_parser.docx_parser import parse_docx
        parsed = parse_docx(path)
    elif suffix == ".doc":
        raise ParserError(
            "Format „.doc” (stari Word binary) nije podržan. "
            "Otvori u Wordu i spremi kao „.docx” ili „.pdf”."
        )
    else:
        raise ParserError(f"Nepodržani format: {suffix}")

    return _inject_subtype(parsed, name_for_subtype)
