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
    "naslovn",  # naslovna, naslovnica, naslovni
    "sadrz",  # sadržaj, sadrzaj
    "sadrž",
    "eksportiraj",  # Apple Numbers TOC export
    "summary",
    "export",
    "title page",
    "cover",
    "toc",
    "korice",
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
    r"^\s*(?:"
    r"[A-ZČĆŽŠĐ]\.?[\s\d.]*\d"           # A1, A.1, A.1.1, A 1
    r"|\d+(?:\.\d+){0,4}\.?"              # 1, 1., 1.1, 1.1.1
    r"|[A-ZČĆŽŠĐ]\.\d+(?:\.\d+){0,3}"     # A.1, A.1.1
    r"|[A-ZČĆŽŠĐ]\.?"                     # A, A. — single Croatian uppercase letter
    r"|[IVXLCM]+\.?"                       # I, II, III, IV, V, VI, VII, VIII, IX, X (roman numerals)
    r")\s*$"
)
# Matches '1', '1.', '1.1', '1.1.1', 'A', 'A.', 'A.1', 'A.1.1', '12', '23.4',
# 'I', 'II', 'III', 'IV', 'V', etc.

# Detection of UKUPNO/total label anywhere in the row text. Per Marko's
# guidance: an UKUPNO row carries the literal "UKUPNO" word (and usually
# the group label/name being summed) — distinct from stavka description
# rows. We use this together with the SUM formula detection so that even
# a hardcoded "UKUPNO" value (no formula) gets caught.
_UKUPNO_LABEL_RE = re.compile(r"\bUKUPNO\b|\bSUBTOTAL\b", re.IGNORECASE)


def _row_has_ukupno_label(
    row: tuple[Cell, ...],
    cache: dict[tuple[int, int], Any] | None = None,
) -> bool:
    """Return True if any cell in `row` contains the literal "UKUPNO" word."""
    for cell in row:
        if cell is None:
            continue
        val = _resolve(cell, cache)
        if isinstance(val, str) and _UKUPNO_LABEL_RE.search(val):
            return True
    return False


def _is_section_label(value: Any) -> bool:
    if value is None:
        return False
    s = str(value).strip()
    if not s:
        return False
    return bool(SECTION_LABEL_RE.match(s))


def _section_depth(label: str) -> int:
    """Heuristic depth ranking for a section label so we can manage a
    nesting stack: single Croatian uppercase letter (A, B, C…) sits at
    depth 1, roman numeral (I, II, III…) at depth 2, plain integer (1,
    2, …) at depth 3, dotted number (1.1, 1.1.1) at depth 4+. This
    mirrors how Croatian troskovnici nest groups → subgroups → stavke."""
    s = (label or "").strip().rstrip(".")
    if not s:
        return 0
    if re.fullmatch(r"\d+(?:\.\d+)+", s):
        return 3 + s.count(".")
    if re.fullmatch(r"\d+", s):
        return 3
    if re.fullmatch(r"[IVXLCM]+", s, re.IGNORECASE) and len(s) >= 1:
        # Roman numerals — but only when the value would actually parse.
        # "I", "II", etc. are common; "A" is a letter and won't reach this.
        return 2
    if re.fullmatch(r"[A-ZČĆŽŠĐ]", s):
        return 1
    if re.fullmatch(r"[A-ZČĆŽŠĐ]\.\d+(?:\.\d+)*", s):
        return 2 + s.count(".")
    # Fallback: treat unknown patterns as deepest so they don't pop ancestors
    return 99


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


def _resolve(cell: Cell | None, cache: dict[tuple[int, int], Any] | None) -> Any:
    """Cell value, but swap in the cached calculated value when the cell
    holds a formula. Lets `=B10` style cross-cell references in opis/label
    columns resolve to the human-readable text the user actually sees."""
    if cell is None:
        return None
    if cache is not None and cell.data_type == "f":
        return cache.get((cell.row, cell.column), cell.value)
    return cell.value


def _str(
    row: tuple[Cell, ...],
    col: int | None,
    cache: dict[tuple[int, int], Any] | None = None,
) -> str:
    cell = _cell(row, col)
    val = _resolve(cell, cache)
    if val is None:
        return ""
    return str(val).strip()


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).replace(",", ".").strip()
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _has_math(row: tuple[Cell, ...], mapping: ColumnMapping) -> bool:
    return any(
        _value(row, c) not in (None, "")
        for c in (mapping.jm, mapping.kol, mapping.cijena, mapping.iznos)
    )


# Markers Marko uses to introduce a list of sub-positions inside an item.
_POSITIONS_HEADER_RE = re.compile(
    r"(?im)^(?:POZICIJE|POZICIJA|POPIS|SUBPOZICIJE|STAVKE|RAZRADA|RAZRAĐUJE)\s*:?\s*$"
)
_POSITION_BULLET_RE = re.compile(r"^\s*[-–•·]\s*(.+?)\s*$")

# UKUPNO / recap detection: a row whose iznos is a SUM(...) formula is
# never an actual stavka — it's either the stavka's own UKUPNO line (when
# the SUM covers rows belonging to that stavka) or a group/recap total
# (when the SUM covers rows from earlier blocks). We use the smallest
# referenced row to tell them apart.
_SUM_FUNC_RE = re.compile(r"\bSUM\s*\(\s*([^)]*)\s*\)", re.IGNORECASE)
_RANGE_REF_RE = re.compile(r"\$?[A-Z]+\$?(\d+)\s*:\s*\$?[A-Z]+\$?(\d+)")
_CELL_REF_RE = re.compile(r"\$?[A-Z]+\$?(\d+)")


def _extract_sum_rows(formula: Any) -> list[int] | None:
    """If `formula` is a SUM(...) expression, return sorted unique list of
    Excel row numbers it aggregates (ranges expanded, single-cell lists
    enumerated). Returns None for non-SUM formulas like `=A1` or `=B5*C5`."""
    if not isinstance(formula, str) or not formula.lstrip().startswith("="):
        return None
    m = _SUM_FUNC_RE.search(formula)
    if m is None:
        return None
    body = m.group(1)
    rows: set[int] = set()
    for rm in _RANGE_REF_RE.finditer(body):
        a, b = int(rm.group(1)), int(rm.group(2))
        for r in range(min(a, b), max(a, b) + 1):
            rows.add(r)
    body_no_ranges = _RANGE_REF_RE.sub("", body)
    for rm in _CELL_REF_RE.finditer(body_no_ranges):
        rows.add(int(rm.group(1)))
    return sorted(rows) if rows else None


def _row_sum_info(row: tuple[Cell, ...]) -> tuple[list[int], str] | None:
    """Scan every cell in `row` for a SUM formula. Return (referenced rows,
    formula text) of the first one found. The iznos column inferred by
    the header detector may not be the column that holds the formula
    (Apple Numbers / non-canonical layouts), so we look at every cell."""
    for cell in row:
        if cell is None or cell.value is None or cell.data_type != "f":
            continue
        rows = _extract_sum_rows(cell.value)
        if rows is not None:
            return rows, str(cell.value)
    return None


# Cross-sheet cell references in formulas. Two flavors are common:
#   'Sheet Name'!$F$46 / 'Sheet Name'!F46   — Excel quoted form
#   SheetName!F46                            — Excel bare (no spaces in name)
#   SheetName.F46                            — Apple Numbers / LibreOffice
# We tolerate `.` only when preceded by `=`/operator/`(`/`,`/`;`/space so it
# can't accidentally match a number literal like `1.5`.
_CROSS_SHEET_RE = re.compile(
    r"(?:'([^']+)'|(?<![A-Za-z0-9_])([A-Za-z_][\w]*))!\$?([A-Z]+)\$?(\d+)"
)
_APPLE_SHEET_RE = re.compile(
    r"(?:^=|[=+\-*/(),;\s])([A-Za-z_][\w]*)\.\$?([A-Z]+)\$?(\d+)"
)


def _extract_cross_sheet_refs(formula: Any) -> list[tuple[str, str, int]]:
    """Return list of (sheet_name, column_letter, row) for every cross-sheet
    cell reference in `formula`. Handles quoted Excel form, bare Excel form,
    and Apple Numbers `Sheet.Cell` form."""
    if not isinstance(formula, str) or not formula.lstrip().startswith("="):
        return []
    out: list[tuple[str, str, int]] = []
    for m in _CROSS_SHEET_RE.finditer(formula):
        sheet = (m.group(1) or m.group(2) or "").strip()
        col = m.group(3)
        row = int(m.group(4))
        if sheet:
            out.append((sheet, col, row))
    for m in _APPLE_SHEET_RE.finditer(formula):
        sheet = (m.group(1) or "").strip()
        col = m.group(2)
        row = int(m.group(3))
        if sheet:
            out.append((sheet, col, row))
    return out


def _row_first_formula(row: tuple[Cell, ...]) -> tuple[str, Any] | None:
    """Return (formula_text, calculated_value_or_None) for the first formula
    cell in `row`. Used in rekapitulacija parsing where the iznos column
    holds either a SUM or a cross-sheet reference."""
    for cell in row:
        if cell is None or cell.value is None or cell.data_type != "f":
            continue
        return str(cell.value), None
    return None


def _row_iznos_value(row: tuple[Cell, ...]) -> Any:
    """Return the rightmost numeric/formula value in `row`. Rekapitulacija
    layouts often skip the canonical column header detection, so we just
    take the last cell that holds something money-like."""
    for cell in reversed(row):
        if cell is None or cell.value in (None, ""):
            continue
        if cell.data_type == "f":
            return cell.value
        if isinstance(cell.value, (int, float)):
            return cell.value
    return None


def _extract_positions(text: str) -> list[str]:
    """Return the list of bullet labels under a 'POZICIJE:' header, if any."""
    if not text:
        return []
    lines = text.splitlines()
    started = False
    out: list[str] = []
    for line in lines:
        if not started:
            if _POSITIONS_HEADER_RE.match(line):
                started = True
            continue
        m = _POSITION_BULLET_RE.match(line)
        if m:
            label = m.group(1).strip()
            if label:
                out.append(label)
            continue
        # Empty line or a line that doesn't look like a bullet → end of list
        if line.strip() == "":
            if out:
                break
            continue
        break
    return out


# ---------------------------------------------------------------------------
# Block model

@dataclass
class _Block:
    label: str = ""
    title: str = ""
    title_row: int | None = None
    description_lines: list[tuple[int, str]] = field(default_factory=list)
    math_rows: list[dict[str, Any]] = field(default_factory=list)
    total_row: dict[str, Any] | None = None
    start_row: int = 0
    sheet: str = ""

    def add_description(self, row_idx: int, text: str) -> None:
        if text and text.strip():
            self.description_lines.append((row_idx, text))

    def add_math(
        self,
        row: tuple[Cell, ...],
        mapping: ColumnMapping,
        row_index: int,
        cache: dict[tuple[int, int], Any] | None = None,
    ) -> None:
        iznos_cell = _cell(row, mapping.iznos)
        kol_value = _resolve(_cell(row, mapping.kol), cache)
        cijena_value = _resolve(_cell(row, mapping.cijena), cache)
        is_formula = bool(iznos_cell and iznos_cell.data_type == "f")
        raw_iznos = (
            cache.get((iznos_cell.row, iznos_cell.column), iznos_cell.value)
            if cache is not None and iznos_cell is not None and iznos_cell.data_type == "f"
            else (iznos_cell.value if iznos_cell is not None else None)
        )
        # Always compute the total when both količina and jed.cijena are
        # numeric, so the UI can compare it to the Excel iznos and flag
        # discrepancies (Tier 1.4 — manipulacija jediničnim cijenama).
        computed_iznos: float | None = None
        kol_num = _num(kol_value)
        cijena_num = _num(cijena_value)
        if kol_num is not None and cijena_num is not None:
            computed_iznos = round(kol_num * cijena_num, 2)
        self.math_rows.append(
            {
                "row": row_index,
                "jm": _str(row, mapping.jm, cache),
                "kol": kol_value,
                "cijena": cijena_value,
                "iznos": raw_iznos,
                "iznos_is_formula": is_formula,
                "computed_iznos": computed_iznos,
            }
        )

    @property
    def is_empty(self) -> bool:
        return not (self.label or self.title or self.description_lines or self.math_rows)

    def merged_text(self) -> str:
        parts: list[str] = []
        if self.title:
            parts.append(self.title)
        parts.extend(text for _, text in self.description_lines)
        return "\n".join(p.strip() for p in parts if p and p.strip())


# ---------------------------------------------------------------------------
# Sheet parsers

EMPTY_BOUNDARY_LIMIT = 2  # 2+ consecutive empty rows close a block


def parse_stavke_sheet(
    ws,
    sheet_name: str,
    cache: dict[tuple[int, int], Any] | None = None,
) -> list[ParsedItem]:
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
    group_sums: list[dict[str, Any]] = []
    current = _Block(sheet=sheet_name, start_row=header_idx + 2)
    empty_streak = 0

    for offset, row in enumerate(rows[header_idx + 1 :], start=header_idx + 2):
        rb_str = _str(row, mapping.rb, cache)
        opis_str = _str(row, mapping.opis, cache)
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

        # UKUPNO / recap intercept: any cell in this row holding a SUM(...)
        # formula means this is not a stavka of its own. It's either the
        # current stavka's own UKUPNO (sum covers rows belonging to that
        # stavka) or a group/recap total (sum covers rows from earlier
        # blocks). We tell them apart by the smallest referenced row.
        sum_info = _row_sum_info(row)
        if sum_info:
            sum_rows, iznos_formula = sum_info
            sum_start = sum_rows[0]
            label_parts = [
                _str(row, c, cache)
                for c in (mapping.opis, mapping.jm, mapping.kol, mapping.cijena)
            ]
            label_text = " ".join(p for p in label_parts if p) or "UKUPNO"
            if not current.is_empty and sum_start >= current.start_row:
                # Stavka's own UKUPNO — attach to current block so we can
                # validate it later, but don't add it as a substavka.
                current.total_row = {
                    "row": offset,
                    "label": label_text,
                    "summed_rows": sum_rows,
                    "formula": iznos_formula,
                }
            else:
                # Group/recap sum — close current block, then collect this
                # sum so we can emit it as a separate "group_sum" item with
                # its own validation downstream.
                if not current.is_empty:
                    blocks.append(current)
                    current = _Block(sheet=sheet_name, start_row=offset)
                group_sums.append(
                    {
                        "row": offset,
                        "label": label_text,
                        "summed_rows": sum_rows,
                        "formula": iznos_formula,
                    }
                )
            continue

        if is_new_section:
            if not current.is_empty:
                blocks.append(current)
            current = _Block(
                label=rb_str,
                title=opis_str,
                title_row=offset if opis_str else None,
                sheet=sheet_name,
                start_row=offset,
            )
            if has_math:
                current.add_math(row, mapping, offset, cache)
            continue

        # Continuation row inside the current block
        if opis_str:
            current.add_description(offset, opis_str)
        if has_math:
            current.add_math(row, mapping, offset, cache)

    if not current.is_empty:
        blocks.append(current)

    # Sheet-wide inventory of math rows (across all stavka blocks). Used
    # to validate group_sum coverage: for each group sum we want to know
    # which math rows fall in its row range and which are missing from
    # the sum's referenced rows.
    sheet_math_inventory: list[dict[str, Any]] = []
    math_inventory_by_row: dict[int, dict[str, Any]] = {}
    for block in blocks:
        for mr in block.math_rows:
            entry = {
                "row": mr.get("row"),
                "iznos": mr.get("iznos"),
                "computed_iznos": mr.get("computed_iznos"),
                "block_label": block.label,
                "block_title": block.title,
            }
            sheet_math_inventory.append(entry)
            if entry["row"] is not None:
                math_inventory_by_row[entry["row"]] = entry

    # Sheet-wide map of every total row (group sums + stavka own UKUPNO)
    # to its raw `summed_rows`. Lets us recursively expand a rollup sum
    # like "Ukupno A1+A2" (which references sub-totals, not math rows)
    # into the leaf math rows that ultimately contribute to it. Handles
    # arbitrary nesting depth via DFS with a visited set.
    total_rows_map: dict[int, list[int]] = {
        gs["row"]: gs["summed_rows"] for gs in group_sums
    }
    for block in blocks:
        if block.total_row:
            total_rows_map[block.total_row["row"]] = block.total_row["summed_rows"]
    math_row_set = set(math_inventory_by_row.keys())

    def _expand_to_leaves(seed_rows: list[int]) -> set[int]:
        """Recursively walk SUM references down to leaf math rows."""
        out: set[int] = set()
        visited: set[int] = set()
        stack: list[int] = list(seed_rows)
        while stack:
            r = stack.pop()
            if r in visited:
                continue
            visited.add(r)
            if r in math_row_set:
                out.add(r)
                continue
            sub = total_rows_map.get(r)
            if sub:
                stack.extend(sub)
        return out

    # Emit items in document order: stavka blocks and group_sums interleaved
    # by their first Excel row.
    ordered: list[tuple[int, str, Any]] = []
    for block in blocks:
        ordered.append((block.start_row, "stavka", block))
    for gs in group_sums:
        ordered.append((gs["row"], "group_sum", gs))
    ordered.sort(key=lambda x: x[0])

    # Stack of currently-open section headers, deepest last. Each stavka
    # inherits this stack as its `path` so the UI can show breadcrumbs and
    # the analyzer can reason about hierarchy ("which subgroup is this in").
    section_stack: list[dict[str, Any]] = []

    items: list[ParsedItem] = []
    for _row_idx, kind, payload in ordered:
        if kind == "group_sum":
            gs = payload
            summed = gs["summed_rows"]
            sum_min, sum_max = min(summed), max(summed)
            sum_set = set(summed)

            # Effective leaf-math coverage: walk through any sub-totals
            # referenced by this SUM. A rollup like =F14+F19 (where F14
            # and F19 are themselves SUMs over stavke) expands to the
            # transitive set of math rows underneath.
            effective = _expand_to_leaves(summed)
            is_rollup = bool(sum_set & set(total_rows_map.keys()))

            # Display rows: every math row this sum ultimately includes.
            # For leaf sums this is the directly-summed math rows. For
            # rollup sums it spans every leaf reached through sub-totals.
            covered_math = [
                math_inventory_by_row[r] for r in sorted(effective)
                if r in math_inventory_by_row
            ]

            # Missing detection. For leaf sums: math rows in [min, max]
            # that aren't referenced. For rollup sums: any math row in
            # [min, max] that isn't transitively covered (sub-total may
            # have skipped some). We also consider the union of widest
            # ranges of sub-totals so a rollup sum doesn't miss leaves
            # below its own row range.
            in_range_rows = {
                mr["row"] for mr in sheet_math_inventory
                if mr["row"] is not None and sum_min <= mr["row"] <= sum_max
            }
            missing_set = in_range_rows - effective - sum_set
            missing = [
                math_inventory_by_row[r] for r in sorted(missing_set)
                if r in math_inventory_by_row
            ]

            items.append(
                ParsedItem(
                    position=len(items),
                    label=(gs["label"] or "UKUPNO")[:200],
                    text=gs["label"] or "UKUPNO",
                    metadata={
                        "sheet": sheet_name,
                        "row": gs["row"],
                        "title_row": gs["row"],
                        "kind": "group_sum",
                        "summed_rows": summed,
                        "effective_summed_rows": sorted(effective),
                        "is_rollup": is_rollup,
                        "formula": gs["formula"],
                        "math_rows_in_range": covered_math,
                        "missing_rows": missing,
                    },
                )
            )
            continue

        block = payload
        text = block.merged_text()
        if not text and not block.math_rows:
            continue
        label_parts = [p for p in (block.label, block.title) if p]
        label = " · ".join(label_parts) or sheet_name

        # Block has descriptive content but no math rows → it's a
        # section/subgroup header or a "general terms" pre-amble, not an
        # actual stavka. Track its label on a stack so following stavke
        # know their hierarchical path; emit it as a slim section_header.
        if not block.math_rows:
            depth = _section_depth(block.label)
            while section_stack and section_stack[-1]["depth"] >= depth and depth > 0:
                section_stack.pop()
            section_stack.append(
                {
                    "depth": depth,
                    "label": block.label,
                    "title": block.title,
                    "row": block.start_row,
                }
            )
            items.append(
                ParsedItem(
                    position=len(items),
                    label=label[:200],
                    text=text,
                    metadata={
                        "sheet": sheet_name,
                        "row": block.start_row,
                        "title_row": block.title_row,
                        "text_rows": [
                            {"row": r, "text": t}
                            for r, t in block.description_lines
                        ],
                        "kind": "section_header",
                        "rb": block.label,
                        "title": block.title,
                        "depth": depth,
                        "path": [
                            {"label": s["label"], "title": s["title"]}
                            for s in section_stack
                        ],
                    },
                )
            )
            continue

        positions = _extract_positions(text)
        # Pair positions with math rows whenever both lists are present
        # and have matching cardinalities. This is Marko's standard
        # convention: "POZICIJE: - nastamba - bazeni …" + N math rows.
        if positions and block.math_rows and len(positions) == len(block.math_rows):
            for label_text, math_row in zip(positions, block.math_rows, strict=True):
                math_row["position_label"] = label_text

        items.append(
            ParsedItem(
                position=len(items),
                label=label[:200],
                text=text,
                metadata={
                    "sheet": sheet_name,
                    "row": block.start_row,
                    "title_row": block.title_row,
                    "text_rows": [
                        {"row": r, "text": t}
                        for r, t in block.description_lines
                    ],
                    "kind": "stavka",
                    "rb": block.label,
                    "math_rows": block.math_rows,
                    "total_row": block.total_row,
                    "positions": positions or None,
                    "path": [
                        {"label": s["label"], "title": s["title"]}
                        for s in section_stack
                    ],
                },
            )
        )
    return items


_RECAP_GRAND_RE = re.compile(r"\bSVEUKUPN|GRAND\s*TOTAL|TOTAL\s*INC\b", re.IGNORECASE)
_RECAP_PDV_RE = re.compile(r"\bPDV\b|\bVAT\b", re.IGNORECASE)
_RECAP_TOTAL_RE = re.compile(r"\bUKUPNO\b|\bSUBTOTAL\b", re.IGNORECASE)
_GROUP_LETTER_RE = re.compile(r"^[A-ZČĆŽŠĐ]\.?$")
_ROMAN_NUM_RE = re.compile(r"^[IVXLCM]+\.?$", re.IGNORECASE)


def parse_rekapitulacija_sheet(
    ws,
    sheet_name: str,
    cache: dict[tuple[int, int], Any] | None = None,
) -> list[ParsedItem]:
    """Structured parse of a Rekapitulacija sheet.

    Each non-empty row becomes one of:
    - recap_section:   group header (A/B/C... + group name, no money column)
    - recap_line:      references another sheet's total via cross-sheet ref
                       OR carries an iznos value pointing at a group/sheet
    - recap_subtotal:  SUM of preceding recap rows (group's own UKUPNO)
    - recap_total:     grand UKUPNO of the rekapitulacija
    - recap_pdv:       PDV/VAT calculation
    - recap_grand:     SVEUKUPNO (UKUPNO + PDV)
    - recap_extra:     hardcoded line with a number but no formula (e.g.
                       "Nepredviđeni radovi 5%")
    """
    items: list[ParsedItem] = []
    rows = list(ws.iter_rows())
    if not rows:
        return items

    section_header: str | None = None  # latest A/B/C group label

    for offset, row in enumerate(rows, start=1):
        cell_strings = []
        for c in row:
            if c is None:
                cell_strings.append("")
                continue
            val = _resolve(c, cache)
            cell_strings.append(str(val).strip() if val not in (None, "") else "")
        if not any(cell_strings):
            continue

        # Sheet-title row (single big descriptive cell, no money / formula)
        sum_info = _row_sum_info(row)
        formula_info = _row_first_formula(row)
        formula = formula_info[0] if formula_info else None
        cross_refs = _extract_cross_sheet_refs(formula or "")
        iznos_value = _row_iznos_value(row)

        # Combined free-text (everything but pure numbers / formulas)
        text_parts = [s for s in cell_strings if s and not s.startswith("=")]
        full_text = " ".join(text_parts).strip()

        # Heuristic: section header — one of the cells is a single uppercase
        # letter (group marker A/B/C…) AND no formula/iznos in the row.
        first_short = next((s for s in cell_strings if s), "")
        is_letter_header = bool(_GROUP_LETTER_RE.match(first_short))
        if (
            is_letter_header
            and not sum_info
            and not formula
            and (iznos_value is None or full_text)
        ):
            # A standalone group header: "A   GRAĐEVINSKO-OBRTNIČKI RADOVI"
            section_header = full_text or first_short
            items.append(
                ParsedItem(
                    position=len(items),
                    label=full_text[:200] or first_short,
                    text=full_text or first_short,
                    metadata={
                        "sheet": sheet_name,
                        "row": offset,
                        "kind": "recap_section",
                        "section": section_header,
                    },
                )
            )
            continue

        # Classify by content priority: SVEUKUPNO > PDV > UKUPNO/SUM > line.
        is_grand = bool(_RECAP_GRAND_RE.search(full_text))
        is_pdv = (not is_grand) and bool(_RECAP_PDV_RE.search(full_text))
        is_ukupno = (
            not is_grand and not is_pdv and bool(_RECAP_TOTAL_RE.search(full_text))
        )

        if is_grand:
            kind = "recap_grand"
        elif is_pdv:
            kind = "recap_pdv"
        elif sum_info or is_ukupno:
            kind = "recap_subtotal" if section_header else "recap_total"
        elif cross_refs:
            kind = "recap_line"
        elif iznos_value is not None:
            # Hardcoded number with descriptive text — additional cost line
            kind = "recap_extra"
        else:
            # Free text with no number — likely a continuation/description
            kind = "recap_section"

        # Title row at the very top (no group context yet, just descriptive text)
        if kind == "recap_section" and not section_header and not is_letter_header:
            # Skip the sheet's title row from generating an item.
            continue

        # Resolve summed rows for SUM formulas
        summed_rows: list[int] = sum_info[0] if sum_info else []
        sum_formula = sum_info[1] if sum_info else None

        # Best-effort label
        label = full_text or section_header or kind.upper()

        items.append(
            ParsedItem(
                position=len(items),
                label=label[:200],
                text=full_text or label,
                metadata={
                    "sheet": sheet_name,
                    "row": offset,
                    "title_row": offset,
                    "kind": kind,
                    "section": section_header,
                    "iznos": iznos_value if not isinstance(iznos_value, str) else None,
                    "iznos_raw": iznos_value,
                    "formula": formula or sum_formula,
                    "cross_sheet_refs": [
                        {"sheet": s, "col": c, "row": r}
                        for (s, c, r) in cross_refs
                    ],
                    "summed_rows": summed_rows or None,
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

def _build_formula_cache(cached_ws) -> dict[tuple[int, int], Any]:
    """Build a (row, col) -> calculated value map for an entire sheet so
    label cells holding `=B10` style references can show what the user
    actually sees instead of the raw formula text."""
    cache: dict[tuple[int, int], Any] = {}
    for row in cached_ws.iter_rows():
        for cell in row:
            if cell.value is not None:
                cache[(cell.row, cell.column)] = cell.value
    return cache


def parse_canonical_xlsx(path: Path) -> ParsedDocument:
    try:
        wb = load_workbook(filename=str(path), data_only=False, read_only=False)
        wb_cached = load_workbook(filename=str(path), data_only=True, read_only=False)
    except InvalidFileException as exc:
        raise ParserError(f"Nevažeći XLSX: {exc}") from exc

    items: list[ParsedItem] = []
    sheets_meta: list[dict[str, Any]] = []

    try:
        for ws in wb.worksheets:
            kind = classify_sheet(ws.title)
            cached_ws = (
                wb_cached[ws.title] if ws.title in wb_cached.sheetnames else None
            )
            cache = _build_formula_cache(cached_ws) if cached_ws is not None else {}

            if kind == "skip":
                sheet_items: list[ParsedItem] = []
            elif kind == "stavke":
                sheet_items = parse_stavke_sheet(ws, ws.title, cache)
            elif kind == "rekapitulacija":
                sheet_items = parse_rekapitulacija_sheet(ws, ws.title, cache)
            else:
                # opci_uvjeti — free-text per row, no structured math
                sheet_items = _raw_text_items(ws, ws.title)
                for it in sheet_items:
                    it.metadata["kind"] = kind

            for item in sheet_items:
                item.position = len(items)
                items.append(item)

            sheets_meta.append({"name": ws.title, "kind": kind, "items": len(sheet_items)})
    finally:
        wb.close()
        wb_cached.close()

    return ParsedDocument(
        items=items,
        metadata={"format": "xlsx", "parser": "canonical-block", "sheets": sheets_meta},
    )
