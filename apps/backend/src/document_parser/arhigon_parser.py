from __future__ import annotations

from pathlib import Path

from src.document_parser.base import ParsedDocument, ParserError


def parse_arhigon(path: Path) -> ParsedDocument:
    """Placeholder parser for the .arhigonfile internal format.

    The format specification is pending. Once delivered, this parser will
    extract structured items from the file. For now we explicitly fail so
    the upload pipeline does not silently accept unsupported documents.
    """
    raise ParserError(
        "Format .arhigonfile još nije podržan — specifikacija je u pripremi."
    )
