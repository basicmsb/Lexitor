from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    chunk_index: int
    page: int | None = None


# Cohere embed-multilingual-v3 ima ~512 token kontekst (cca ~2000 znakova HR jezika).
# Cijemo ostati ispod toga sa rezervom — ~1600 znakova po chunku, ~200 overlap.
_TARGET_CHARS = 1600
_OVERLAP_CHARS = 200
_PAGE_SEP = "\n\f\n"


def chunk_text(text: str) -> list[Chunk]:
    """Split full-document text into overlapping chunks, page-aware.

    1. Split on form-feed page separators (extract_pdf_text inserts them).
    2. Within each page, split on paragraph breaks.
    3. Greedily pack paragraphs until ~1600 chars, then start new chunk
       with a 200 char overlap from the previous one.
    """
    if not text.strip():
        return []

    chunks: list[Chunk] = []
    chunk_index = 0

    pages = text.split(_PAGE_SEP) if _PAGE_SEP in text else [text]

    for page_no, page_text in enumerate(pages, start=1):
        page_text = page_text.strip()
        if not page_text:
            continue

        paragraphs = [p.strip() for p in page_text.split("\n\n") if p.strip()]
        buffer = ""
        for paragraph in paragraphs:
            if not buffer:
                buffer = paragraph
                continue
            if len(buffer) + len(paragraph) + 2 <= _TARGET_CHARS:
                buffer += "\n\n" + paragraph
                continue

            chunks.append(Chunk(text=buffer.strip(), chunk_index=chunk_index, page=page_no))
            chunk_index += 1
            tail = buffer[-_OVERLAP_CHARS:]
            buffer = (tail + "\n\n" + paragraph).strip()

        if buffer.strip():
            chunks.append(Chunk(text=buffer.strip(), chunk_index=chunk_index, page=page_no))
            chunk_index += 1

    return chunks
