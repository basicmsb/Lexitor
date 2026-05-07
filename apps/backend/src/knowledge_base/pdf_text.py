from __future__ import annotations

import re
from pathlib import Path

import pdfplumber


def extract_pdf_text(path: Path) -> str:
    """Extract a normalized full-text representation of a PDF.

    Joins pages with form-feed markers so the chunker can detect natural
    boundaries. Collapses repeated whitespace to keep embeddings stable.
    """
    pages: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages.append(text.strip())
    raw = "\n\f\n".join(pages)
    # Collapse 3+ consecutive newlines to 2 (paragraph break)
    cleaned = re.sub(r"\n{3,}", "\n\n", raw)
    # Normalise stray whitespace inside lines
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    return cleaned.strip()
