"""Deterministic per-item rules. Each rule is a pure function that
takes the parsed item (text + metadata) and returns zero or more
Findings — never modifies anything. The mock analyzer runs every rule
on each item, collects findings, and falls back to the random demo
mock only when no real rule fires.

A finding is a plain dict (not a model) so it round-trips through
JSONB without ORM gymnastics:
    {
        "kind": "brand_lock",
        "status": "fail",
        "explanation": "...",
        "suggestion": "...",
        "is_mock": False,
        "citations": [{"source": "zjn", "reference": "Članak 207. ZJN", ...}],
    }
"""

from __future__ import annotations

import re
from typing import Any

from src.models import AnalysisItemStatus, TroskovnikType

# ---------------------------------------------------------------------------
# Citation placeholders


_PLACEHOLDER_ZJN_207 = {
    "source": "zjn",
    "reference": "Članak 207. ZJN",
    "snippet": (
        "Kada se u tehničkoj specifikaciji upućuje na konkretnu marku, mora se "
        "dodati riječ „ili jednakovrijedno”."
    ),
    "url": "https://narodne-novine.nn.hr/clanci/sluzbeni/2016_12_120_2607.html",
}


def _make(
    kind: str,
    status: AnalysisItemStatus,
    explanation: str,
    suggestion: str | None = None,
    *,
    is_mock: bool = False,
    citations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Helper to build a finding dict consistently."""
    return {
        "kind": kind,
        "status": status.value,
        "explanation": explanation,
        "suggestion": suggestion,
        "is_mock": is_mock,
        "citations": citations or [],
    }


# ---------------------------------------------------------------------------
# Rules — each returns list[finding] (possibly empty)


def _math_rows(meta: dict[str, Any]) -> list[dict[str, Any]]:
    rows = meta.get("math_rows") if isinstance(meta, dict) else None
    return rows if isinstance(rows, list) else []


def _has_text_value(value: Any) -> bool:
    """True if `value` is a non-empty string after trimming."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return False


def _is_numeric(value: Any) -> bool:
    """True if `value` parses as a finite number (not "—", not formula text)."""
    if value is None or value == "":
        return False
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        import math

        return math.isfinite(value)
    s = str(value).replace(",", ".").strip()
    if not s or s.startswith("="):
        return False
    try:
        f = float(s)
        import math

        return math.isfinite(f)
    except (TypeError, ValueError):
        return False


def rule_missing_jm(text: str, meta: dict[str, Any]) -> list[dict[str, Any]]:
    """Math rows must have a unit of measure. Without JM the bid quantity
    is ambiguous (kom? m? m²?) and the procurement is non-comparable."""
    rows = _math_rows(meta)
    missing = [
        r for r in rows
        if (_is_numeric(r.get("kol")) or _is_numeric(r.get("cijena")))
        and not _has_text_value(r.get("jm"))
    ]
    if not missing:
        return []
    return [
        _make(
            "missing_jm",
            AnalysisItemStatus.WARN,
            (
                f"{len(missing)} math redaka nema jedinicu mjere — kvantiteta "
                f"je nejasna (kom? m? m²?). Ponuditelji ne mogu usporediti "
                f"bidove na istoj osnovi."
            ),
            "Dodati jedinicu mjere za svaki red s količinom ili cijenom.",
            citations=[dict(_PLACEHOLDER_ZJN_207)],
        )
    ]


def rule_missing_kol(text: str, meta: dict[str, Any]) -> list[dict[str, Any]]:
    """A row with a unit price but no quantity is suspicious — either it's
    a placeholder or the quantity belongs in another column."""
    rows = _math_rows(meta)
    missing = [
        r for r in rows
        if _is_numeric(r.get("cijena"))
        and not _is_numeric(r.get("kol"))
        and not _has_text_value(r.get("kol"))
    ]
    if not missing:
        return []
    return [
        _make(
            "missing_kol",
            AnalysisItemStatus.WARN,
            (
                f"{len(missing)} math redaka ima jediničnu cijenu, ali ne i "
                f"količinu. Bez količine ne može se utvrditi ukupni iznos."
            ),
            "Provjeriti popunjenost stupca Količina za sve math retke.",
            citations=[dict(_PLACEHOLDER_ZJN_207)],
        )
    ]


def rule_missing_cijena(
    text: str,
    meta: dict[str, Any],
    troskovnik_type: TroskovnikType | None = None,
) -> list[dict[str, Any]]:
    """Math row with quantity but no unit price.

    Pravilo ovisi o tipu troškovnika (vidi project_lexitor_troskovnik_tipovi.md):
    - Ponudbeni: prazna jed. cijena je **očekivana** (popunjava ponuditelj)
      → NE fire-amo nalaz
    - Procjena: jed. cijena MORA biti popunjena → FAIL
    - Nepoznato: ostaje WARN (kao prije)"""
    if troskovnik_type == TroskovnikType.PONUDBENI:
        return []
    rows = _math_rows(meta)
    missing = [
        r for r in rows
        if _is_numeric(r.get("kol"))
        and not _is_numeric(r.get("cijena"))
        and not _has_text_value(r.get("cijena"))
    ]
    if not missing:
        return []
    severity = (
        AnalysisItemStatus.FAIL
        if troskovnik_type == TroskovnikType.PROCJENA
        else AnalysisItemStatus.WARN
    )
    return [
        _make(
            "missing_cijena",
            severity,
            (
                f"{len(missing)} math redaka ima količinu, ali jedinična "
                f"cijena nije popunjena. Stavka se ne može vrednovati."
            ),
            "Popuniti stupac Jed. cijena ili izričito označiti redove kao "
            "podstavke (bez vlastite cijene).",
            citations=[dict(_PLACEHOLDER_ZJN_207)],
        )
    ]


def rule_missing_opis(text: str, meta: dict[str, Any]) -> list[dict[str, Any]]:
    """A stavka with math values but no description text at all is a
    serious red flag — bidders can't price what they can't read."""
    rows = _math_rows(meta)
    if not rows:
        return []
    has_any_math = any(
        _is_numeric(r.get("kol")) or _is_numeric(r.get("cijena")) or _is_numeric(r.get("iznos"))
        for r in rows
    )
    if not has_any_math:
        return []
    text_present = (text and text.strip()) or any(
        _has_text_value(r.get("position_label")) for r in rows
    )
    if text_present:
        return []
    return [
        _make(
            "missing_opis",
            AnalysisItemStatus.FAIL,
            "Stavka ima math vrijednosti, ali nema nikakvog opisa.",
            "Dodati opis stavke — što se točno traži, koje su minimalne "
            "tehničke karakteristike, norma izvedbe.",
            citations=[dict(_PLACEHOLDER_ZJN_207)],
        )
    ]


def rule_zero_unit_price(
    text: str,
    meta: dict[str, Any],
    troskovnik_type: TroskovnikType | None = None,
) -> list[dict[str, Any]]:
    """Unit price is exactly 0 with quantity > 0 — placeholder.

    Za ponudbeni troškovnik 0,00 je očekivano (ponuditelj će popuniti),
    pa NE fire-amo. Za procjenu i nepoznato fire-amo WARN."""
    if troskovnik_type == TroskovnikType.PONUDBENI:
        return []
    rows = _math_rows(meta)
    flagged = [
        r for r in rows
        if _is_numeric(r.get("kol"))
        and float(str(r.get("kol")).replace(",", ".")) > 0
        and _is_numeric(r.get("cijena"))
        and float(str(r.get("cijena")).replace(",", ".")) == 0
    ]
    if not flagged:
        return []
    return [
        _make(
            "zero_unit_price",
            AnalysisItemStatus.WARN,
            (
                f"{len(flagged)} math redaka ima jediničnu cijenu 0,00 € uz "
                f"količinu > 0. Vjerojatno placeholder — provjeriti."
            ),
            "Popuniti stvarnu jediničnu cijenu ili izbrisati red ako nije "
            "primjenjiv.",
            citations=[dict(_PLACEHOLDER_ZJN_207)],
        )
    ]


# ---------------------------------------------------------------------------
# Master entry point


ALL_RULES = [
    rule_missing_opis,
    rule_missing_jm,
    rule_missing_kol,
    rule_missing_cijena,
    # rule_vague_opis je uklonjen 2026-05-09 — bez ground-truth korpusa
    # "stručno napisanih stavki" (čeka Arhigon-ovu eksperizirano recenziranu
    # bazu), brojanje znakova nije relevantna provjera.
    rule_zero_unit_price,
]

# Rules koja prihvaćaju troskovnik_type (pravilo o praznoj jed. cijeni
# ovisi o tipu — ponudbeni vs procjena, vidi project_lexitor_troskovnik_tipovi.md).
_RULES_WITH_TYPE = {rule_missing_cijena, rule_zero_unit_price}


def run_per_row_rules(
    text: str,
    meta: dict[str, Any] | None,
    troskovnik_type: TroskovnikType | None = None,
) -> list[dict[str, Any]]:
    """Run every per-row rule. Returns a flat list of findings (possibly
    empty). Caller appends domain-specific findings (brand check,
    arithmetic, group_sum, recap) on top.

    `troskovnik_type` se prosljeđuje samo onim pravilima koja ovise o
    njemu (rule_missing_cijena, rule_zero_unit_price)."""
    metadata = meta or {}
    out: list[dict[str, Any]] = []
    for rule in ALL_RULES:
        try:
            if rule in _RULES_WITH_TYPE:
                out.extend(rule(text or "", metadata, troskovnik_type))
            else:
                out.extend(rule(text or "", metadata))
        except Exception:
            # A single broken rule shouldn't take down the whole analysis;
            # log and continue. We deliberately don't re-raise.
            import logging

            logging.getLogger(__name__).exception("rule %s raised", rule.__name__)
    return out
