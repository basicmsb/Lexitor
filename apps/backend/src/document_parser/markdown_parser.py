"""DON tekst/markdown parser — radi s .md (EOJN-ov format) i .txt
(kad korisnik copy-paste s viewer-a u Notepad pa nestanu # markeri).

Strategija (dva tipa hint-a strukture):
1. **`#` / `##` / `###` markdown headers** — eksplicitno (kad pošten markdown)
2. **Dotted rb na poČetku reda** (`1.`, `2.3.`, `4.1.1.`) — DON konvencija
   koja je sačuvana i u plain text-u kad se markdown sintaksa izgubi.
   Depth = broj točki u rb (`1.` depth=1, `1.2.` depth=2, `1.2.3.` depth=3).
3. **ALL CAPS heading** (npr. "PODACI O PONUDI", "DIO II") — sekundarni
   marker kad nema rb-a.

Blokovi su separirani praznim redovima. Each block je analyzable jedinica.

Output ParsedItem.metadata.kind:
- section_header — # marker, dotted-rb header, ili ALL CAPS heading
- paragraph — slobodan paragraf
- requirement — paragraf s "ponuditelj mora", "minimalna", "ISO …"
- criterion — paragraf s "kriterij", "bodov", "ENP"
- deadline — paragraf s datumom + rok keywords
- list — bullet/numerated lista
- table — markdown tablica
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.document_parser.base import ParsedDocument, ParsedItem, ParserError

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
# Dotted rb na početku linije: "1.", "1.1.", "2.3.4.", "A.", "B.II.1."
# Glavna razlika od ostalih dotted brojeva (1.500,00 cijene) — mora biti
# na početku linije + iza space + tekst.
_RB_PREFIX_RE = re.compile(
    r"^(\d+(?:\.\d+)*\.?|[A-ZČĆŽŠĐ](?:\.\d+)*\.?)\s+(.+)$"
)
# ALL CAPS heading: 3+ velika slova + opcionalne razmake/brojevi
_ALLCAPS_RE = re.compile(r"^[A-ZČĆŽŠĐ0-9][A-ZČĆŽŠĐ0-9\s\-\–\.]{4,}$")
_LIST_RE = re.compile(r"^\s*([-*+]|\d+\.)\s+(.+)$")
_TABLE_RE = re.compile(r"^\s*\|.*\|\s*$")
_DEADLINE_KEYWORDS = (
    "rok", "rokovi", "datum", "vrijeme", "krajnji", "podnošenje",
    "isporuk", "izvod", "dostava",
)
_REQUIREMENT_KEYWORDS = (
    "ponuditelj mora", "ponuditelj je dužan", "ponuditelj treba",
    "obvezna referenc", "minimalna", "najmanje", "ne manje od",
    "iso ", "hrn ", "certifikat",
)
_CRITERION_KEYWORDS = (
    "kriterij", "ocjenjivanje", "bodov", "ekonomski najpovoljnij",
    "enp", "vagiranj",
)


def _classify_block(text: str) -> str:
    """Heuristika za kind paragrafa. Lower-case search."""
    lower = text.lower()
    # Tablica zauzima cijeli blok
    if _TABLE_RE.match(text.strip().split("\n")[0]):
        return "table"
    # Lista — sve linije počinju s -, *, + ili broj.
    lines = [l for l in text.split("\n") if l.strip()]
    if lines and all(_LIST_RE.match(l) for l in lines):
        return "list"
    # Deadline — sadrži datum-pattern + ključne riječi
    if any(k in lower for k in _DEADLINE_KEYWORDS) and re.search(
        r"\d{1,2}\.\s*\d{1,2}\.\s*\d{2,4}|\d+\s*(dan|sat|tjedn|mjeseci|godin)",
        lower,
    ):
        return "deadline"
    # Kriterij
    if any(k in lower for k in _CRITERION_KEYWORDS):
        return "criterion"
    # Uvjet sposobnosti
    if any(k in lower for k in _REQUIREMENT_KEYWORDS):
        return "requirement"
    return "paragraph"


def _split_blocks(body: str) -> list[str]:
    """Dijeli markdown body na blokove razdvojene praznim redovima.

    Liste i tablice ostaju cjeline (uzastopne linije bez praznog reda)."""
    blocks: list[str] = []
    current: list[str] = []
    for line in body.split("\n"):
        if line.strip() == "":
            if current:
                blocks.append("\n".join(current).strip())
                current = []
        else:
            current.append(line)
    if current:
        blocks.append("\n".join(current).strip())
    return [b for b in blocks if b]


def _extract_rb(text: str) -> tuple[str | None, str]:
    """Ako paragraf počinje s rb-om (1.1, 2.3.4, A., …), vrati (rb, ostatak).
    Inače vrati (None, original)."""
    first_line = text.split("\n", 1)[0]
    m = _RB_PREFIX_RE.match(first_line)
    if not m:
        return None, text
    rb = m.group(1)
    # Sigurnost: ne tretirati cijene (1.500,00) ili decimale kao rb
    if "," in rb:
        return None, text
    rest = m.group(2)
    rest_full = rest + (text[len(first_line):] if len(text) > len(first_line) else "")
    return rb, rest_full.strip()


def parse_markdown(path: Path) -> ParsedDocument:
    """Parsa .md fajl u ParsedDocument s DON-specific kindovima."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Fallback — neka EOJN-ova .md datoteka može biti CP1250 / Latin-2
        text = path.read_text(encoding="cp1250", errors="replace")
    except Exception as exc:  # noqa: BLE001
        raise ParserError(f"Ne mogu čitati {path.name}: {exc}") from exc
    return parse_text(text, source_format="markdown", filename=path.name)


def parse_text(
    text: str,
    source_format: str = "markdown",
    filename: str = "",
) -> ParsedDocument:
    """Parsa već učitani tekst (markdown ili docx-konvertiran) u ParsedDocument.

    Koriste je i `parse_markdown` (čita .md/.txt) i `parse_docx`
    (konvertira .docx u markdown-like tekst pa zove ovu funkciju)."""
    items: list[ParsedItem] = []
    current_chapter: dict[str, Any] | None = None
    chapter_stack: list[dict[str, Any]] = []  # za hijerarhiju
    block_buffer: list[str] = []

    def flush_blocks():
        """Pretvori block_buffer u ParsedItem-e."""
        if not block_buffer:
            return
        joined = "\n".join(block_buffer).strip()
        if not joined:
            block_buffer.clear()
            return
        for block_text in _split_blocks(joined):
            rb, body = _extract_rb(block_text)
            kind = _classify_block(body)
            # Title — prva linija ako je kratka
            first_line = body.split("\n", 1)[0]
            title = first_line if len(first_line) <= 120 else ""
            items.append(
                ParsedItem(
                    position=len(items),
                    label=title or body[:120],
                    text=body,
                    metadata={
                        "sheet": "DON",
                        "kind": kind,
                        "rb": rb,
                        "title": title,
                        "chapter_path": [
                            {"depth": c["depth"], "title": c["title"]}
                            for c in chapter_stack
                        ],
                    },
                )
            )
        block_buffer.clear()

    def emit_section_header(depth: int, title: str, rb: str | None = None):
        """Pop stack do depth i push novi chapter, emit section_header."""
        while chapter_stack and chapter_stack[-1]["depth"] >= depth:
            chapter_stack.pop()
        chapter_stack.append({"depth": depth, "title": title})
        label = f"{rb} {title}" if rb else title
        items.append(
            ParsedItem(
                position=len(items),
                label=label[:200],
                text=label,
                metadata={
                    "sheet": "DON",
                    "kind": "section_header",
                    "depth": depth,
                    "rb": rb,
                    "title": title,
                    "chapter_path": [
                        {"depth": c["depth"], "title": c["title"]}
                        for c in chapter_stack
                    ],
                },
            )
        )

    def is_likely_section_line(line: str) -> tuple[int, str, str | None] | None:
        """Vrati (depth, title, rb) ako linija izgleda kao section header,
        inače None.

        Tri detektora:
        1. Markdown `#` header
        2. Dotted rb prefix ("1.", "2.3.", "1.1.1.") + tekst nakon
        3. ALL CAPS line (4+ uppercase chars), ne unutar paragrafa
        """
        s = line.strip()
        if not s:
            return None
        m = _HEADING_RE.match(s)
        if m:
            return len(m.group(1)), m.group(2).strip(), None
        m = _RB_PREFIX_RE.match(s)
        if m:
            rb = m.group(1)
            rest = m.group(2).strip()
            # Filter: rb mora biti dotted i kratak (ne npr. "1500,00 EUR")
            if "," in rb or "EUR" in rb.upper():
                return None
            # Heading-like: rest je <= ~150 znakova bez period mid-rečenice
            # (paragraf bi imao više rečenica i zapete)
            if len(rest) <= 150 and rest.count(". ") <= 1:
                segments = [seg for seg in rb.split(".") if seg.strip()]
                depth = len(segments)
                return depth, rest, rb
        # ALL CAPS heading — npr. "PODACI O PONUDI", "DIO II – Upute"
        if _ALLCAPS_RE.match(s) and len(s) <= 100:
            return 1, s, None
        return None

    for raw_line in text.split("\n"):
        # Heading detekcija — koristi 3-detektor
        # SAMO ako je line "stand-alone" (prazan red prije/poslije, ili
        # bez tekućeg paragrafa)
        if not block_buffer or block_buffer[-1].strip() == "":
            sec = is_likely_section_line(raw_line)
            if sec is not None:
                flush_blocks()
                depth, title, rb = sec
                emit_section_header(depth, title, rb)
                continue
        block_buffer.append(raw_line)
    flush_blocks()

    return ParsedDocument(
        items=items,
        metadata={
            "format": source_format,
            "parser": "don-markdown",
            "filename": filename,
        },
    )
