from __future__ import annotations

from pathlib import Path

import pdfplumber

from src.document_parser.base import ParsedDocument, ParsedItem, ParserError


def parse_pdf(path: Path) -> ParsedDocument:
    items: list[ParsedItem] = []
    page_count = 0
    try:
        with pdfplumber.open(str(path)) as pdf:
            page_count = len(pdf.pages)
            for page_index, page in enumerate(pdf.pages):
                tables = page.extract_tables() or []
                if tables:
                    for table_index, table in enumerate(tables):
                        for row_index, row in enumerate(table):
                            cells = [c.strip() for c in row if c]
                            if not cells:
                                continue
                            text = " | ".join(cells)
                            items.append(
                                ParsedItem(
                                    position=len(items),
                                    text=text,
                                    label=f"Stranica {page_index + 1}, tablica {table_index + 1}, red {row_index + 1}",
                                    metadata={
                                        "page": page_index + 1,
                                        "table": table_index + 1,
                                        "row": row_index + 1,
                                        "source": "table",
                                    },
                                )
                            )
                    continue

                text = page.extract_text() or ""
                for paragraph_index, raw in enumerate(text.split("\n\n")):
                    chunk = raw.strip()
                    if not chunk:
                        continue
                    items.append(
                        ParsedItem(
                            position=len(items),
                            text=chunk,
                            label=f"Stranica {page_index + 1}, odlomak {paragraph_index + 1}",
                            metadata={
                                "page": page_index + 1,
                                "paragraph": paragraph_index + 1,
                                "source": "text",
                            },
                        )
                    )
    except Exception as exc:  # pdfplumber has no specialised exception class
        raise ParserError(f"PDF parsing nije uspio: {exc}") from exc

    return ParsedDocument(
        items=items,
        metadata={"format": "pdf", "page_count": page_count},
    )
