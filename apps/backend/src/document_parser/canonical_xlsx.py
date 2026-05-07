"""Block-oriented XLSX parser for Arhigon-style troskovnici.

Per Marko's guidance: Lexitor cares about *blocks of text* — one block =
one entity that the analyzer reasons about against ZJN/DKOM. We don't
need to model groups, sub-items, or unit-quantity columns precisely;
those details cost engineering effort but add little to the legal
analysis. We do still flag the math row(s) for a future deterministic
validator, but the primary product of the parser is the *merged text*
of each entity.

A block starts when:
    - column with R.b. (auto-detected) gets a new section/item label, OR
    - column with R.b. is empty for ≥ 2 consecutive rows after content
A block ends right before the next block starts. Pure header rows,
naslovnica/sadrzaj sheets and Numbers TOC sheets are skipped.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from openpyxl.cell.cell import Cell
from openpyxl.utils.exceptions import InvalidFileException

from src.document_parser.base import ParsedDocument, ParsedItem, ParserError

# ---------------------------------------------------------------------------
# Sheet classification

SKIP_SHEET_TOKENS = (
    "naslovnic",
    "sadrz",
    "sadrž",
    "eksportiraj",
    "summary",
    "export",
    "title page",
    "cover",
    "toc",
)
OPCI_UVJETI_TOKENS = ("opci uvj", "opće uvj", "opce uvj", "general cond")
REKAPITULACIJA_TOKENS = ("rekapitul", "recapitul", "summary of works")


def _normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9čćžšđ]+", " ", text.lower()).strip()


def classify_sheet(name: str) -> str:
    norm = _normalise(name)
    if any(tok in norm for tok in SKIP_SHEET_TOKENS):
        return "skip"
    if any(tok in norm for tok in OPCI_UVJETI_TOKENS):
        return "opci_uvjeti"
    if any(tok in norm for tok in REKAPITULACIJA_TOKENS):
        return "rekapitulacija"
    return "stavke"


# ---------------------------------------------------------------------------
# Header / column detection

HEADER_TOKENS: dict[str, tuple[str, ...]] = {
    "rb": ("redni broj", "r b", "rb", "r br", "br", "broj"),
    "opis": ("opis stavke", "opis", "naziv stavke", "naziv", "stavka", "predmet", "description"),
    "jm": ("jedinica mjere", "jed mjere", "jed mj", "jm", "jedinica", "mjera", "unit"),
    "kol": ("kolicina stavke", "kolicina", "kol", "qty", "količina", "količ"),
    "cijena": ("jedinicna cijena", "jed cijena", "jedinicna", "cijena", "price"),
    "iznos": ("ukupna cijena", "ukupno", "iznos", "total", "vrijednost"),
}


@dataclass
class ColumnMapping:
    rb: int | None = None
    opis: int | None = None
    jm: int | None = None
    kol: int | None = None
    cijena: int | None = None
    iznos: int | None = None

    @property
    def is_minimally_complete(self) -> bool:
        return self.opis is not None


def _match_role(text: str) -> str | None:
    norm = _normalise(text)
    if not norm:
        return None
    for role, tokens in HEADER_TOKENS.items():
        for tok in sorted(tokens, key=len, reverse=True):
            if tok in norm:
                return role
    return None


def _row_to_strings(row: tuple[Cell, ...]) -> list[str]:
    return [
        ("" if c.value is None else str(c.value).replace("\n", " ").replace("\r", " "))
        for c in row
    ]


def find_header(rows: list[tuple[Cell, ...]]) -> tuple[int, ColumnMapping] | None:
    for idx, row in enumerate(rows[:80]):
        cells = _row_to_strings(row)
        mapping = ColumnMapping()
        hits = 0
        for col_idx, text in enumerate(cells):
            role = _match_role(text)
            if role is None or getattr(mapping, role) is not None:
                continue
            setattr(mapping, role, col_idx)
            hits += 1
        if hits >= 2 and mapping.is_minimally_complete:
            return idx, mapping
    return None


# ---------------------------------------------------------------------------
# R.b. column fallback

SECTION_LABEL_RE = re.compile(
    r"^\s*(?:[A-ZČĆŽŠĐ]\.?[\s\d.]*\d|\d+(?:\.\d+){0,4}\.?|[A-ZČĆŽŠĐ]\.\d+(?:\.\d+){0,3})\s*$"
)
# Matches '1', '1.', '1.1', '1.1.1', 'A', 'A.', 'A.1', 'A.1.1', '12', '23.4'


def _is_section_label(value: Any) -> bool:
    if value is None:
        return False
    s = str(value).strip()
    if not s:
        return False
    return bool(SECTION_LABEL_RE.match(s))


def detect_rb_column(
    sample_rows: list[tuple[Cell, ...]], mapping: ColumnMapping
) -> ColumnMapping:
    if mapping.rb is not None:
        return mapping
    used = {mapping.opis, mapping.jm, mapping.kol, mapping.cijena, mapping.iznos}
    score: dict[int, int] = {}
    for row in sample_rows:
        for col_idx in range(min(len(row), 8)):
            if col_idx in used:
                continue
            cell = row[col_idx]
            if cell.value is None:
                continue
            if _is_section_label(cell.value):
                score[col_idx] = score.get(col_idx, 0) + 1
    if score:
        best_col, best_count = max(score.items(), key=lambda kv: kv[1])
        if best_count >= 2:
            mapping.rb = best_col
    return mapping


# ---------------------------------------------------------------------------
# Cell helpers

def _cell(row: tuple[Cell, ...], col: int | None) -> Cell | None:
    if col is None or col >= len(row):
        return None
    return row[col]


def _value(row: tuple[Cell, ...], col: int | None) -> Any:
    cell = _cell(row, col)
    return cell.value if cell is not None else None


def _str(row: tuple[Cell, ...], col: int | None) -> str:
    val = _value(row, col)
    if val is None:
        return ""
    return str(val).strip()


def _has_math(row: tuple[Cell, ...], mapping: ColumnMapping) -> bool:
    return any(
        _value(row, c) not in (None, "")
        for c in (mapping.jm, mapping.kol, mapping.cijena, mapping.iznos)
    )


# ---------------------------------------------------------------------------
# Block model

@dataclass
class _Block:
    label: str = ""
    title: str = ""
    description_lines: list[str] = field(default_factory=list)
    math_rows: list[dict[str, Any]] = field(default_factory=list)
    start_row: int = 0
    sheet: str = ""

    def add_description(self, text: str) -> None:
        if text:
            self.description_lines.append(text)

    def add_math(self, row: tuple[Cell, ...], mapping: ColumnMapping, row_index: int) -> None:
        iznos_cell = _cell(row, mapping.iznos)
        self.math_rows.append(
            {
                "row": row_index,
                "jm": _str(row, mapping.jm),
                "kol": _value(row, mapping.kol),
                "cijena": _value(row, mapping.cijena),
                "iznos": iznos_cell.value if iznos_cell is not None else None,
                "iznos_is_formula": bool(iznos_cell and iznos_cell.data_type == "f"),
            }
        )

    @property
    def is_empty(self) -> bool:
        return not (self.label or self.title or self.description_lines or self.math_rows)

    def merged_text(self) -> str:
        parts: list[str] = []
        if self.title:
            parts.append(self.title)
        parts.extend(self.description_lines)
        return "\n".join(p.strip() for p in parts if p and p.strip())


# ---------------------------------------------------------------------------
# Sheet parsers

EMPTY_BOUNDARY_LIMIT = 2  # 2+ consecutive empty rows close a block


def parse_stavke_sheet(ws, sheet_name: str) -> list[ParsedItem]:
    rows = list(ws.iter_rows())
    if not rows:
        return []

    header_info = find_header(rows)
    if header_info is None:
        return _raw_text_items(ws, sheet_name)

    header_idx, mapping = header_info
    sample = rows[header_idx + 1 : header_idx + 41]
    mapping = detect_rb_column(sample, mapping)

    blocks: list[_Block] = []
    current = _Block(sheet=sheet_name, start_row=header_idx + 2)
    empty_streak = 0

    for offset, row in enumerate(rows[header_idx + 1 :], start=header_idx + 2):
        rb_str = _str(row, mapping.rb)
        opis_str = _str(row, mapping.opis)
        has_math = _has_math(row, mapping)

        is_empty = not (rb_str or opis_str or has_math)
        is_new_section = bool(rb_str and _is_section_label(rb_str))

        if is_empty:
            empty_streak += 1
            if empty_streak >= EMPTY_BOUNDARY_LIMIT and not current.is_empty:
                blocks.append(current)
                current = _Block(sheet=sheet_name, start_row=offset)
            continue

        # Non-empty row resets streak
        empty_streak = 0

        if is_new_section:
            if not current.is_empty:
                blocks.append(current)
            current = _Block(
                label=rb_str,
                title=opis_str,
                sheet=sheet_name,
                start_row=offset,
            )
            if has_math:
                current.add_math(row, mapping, offset)
            continue

        # Continuation row inside the current block
        if opis_str:
            current.add_description(opis_str)
        if has_math:
            current.add_math(row, mapping, offset)

    if not current.is_empty:
        blocks.append(current)

    items: list[ParsedItem] = []
    for block in blocks:
        text = block.merged_text()
        if not text and not block.math_rows:
            continue
        label_parts = [p for p in (block.label, block.title) if p]
        label = " · ".join(label_parts) or sheet_name
        items.append(
            ParsedItem(
                position=len(items),
                label=label[:200],
                text=text,
                metadata={
                    "sheet": sheet_name,
                    "row": block.start_row,
                    "kind": "stavka",
                    "rb": block.label,
                    "math_rows": block.math_rows,
                },
            )
        )
    return items


def _raw_text_items(ws, sheet_name: str) -> list[ParsedItem]:
    """Fallback for sheets without a recognisable header — every non-empty
    row becomes a standalone item. Used for opci_uvjeti, rekapitulacija,
    and any unrecognised sheet structure."""
    items: list[ParsedItem] = []
    for idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
        cells = [str(c).strip() for c in row if c not in (None, "")]
        if not cells:
            continue
        text = " ".join(cells)
        items.append(
            ParsedItem(
                position=len(items),
                label=f"{sheet_name} · red {idx}",
                text=text,
                metadata={"sheet": sheet_name, "row": idx, "kind": "raw_text"},
            )
        )
    return items


# ---------------------------------------------------------------------------
# Public entry

def parse_canonical_xlsx(path: Path) -> ParsedDocument:
    try:
        wb = load_workbook(filename=str(path), data_only=False, read_only=False)
    except InvalidFileException as exc:
        raise ParserError(f"Nevažeći XLSX: {exc}") from exc

    items: list[ParsedItem] = []
    sheets_meta: list[dict[str, Any]] = []

    try:
        for ws in wb.worksheets:
            kind = classify_sheet(ws.title)
            if kind == "skip":
                sheet_items: list[ParsedItem] = []
            elif kind == "stavke":
                sheet_items = parse_stavke_sheet(ws, ws.title)
            else:
                # opci_uvjeti, rekapitulacija — also free-text per row
                sheet_items = _raw_text_items(ws, ws.title)
                for it in sheet_items:
                    it.metadata["kind"] = kind

            for item in sheet_items:
                item.position = len(items)
                items.append(item)

            sheets_meta.append({"name": ws.title, "kind": kind, "items": len(sheet_items)})
    finally:
        wb.close()

    return ParsedDocument(
        items=items,
        metadata={"format": "xlsx", "parser": "canonical-block", "sheets": sheets_meta},
    )
