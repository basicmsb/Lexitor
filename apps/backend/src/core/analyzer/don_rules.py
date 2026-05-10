"""DON-specifična pravila — modularan registry.

Svako novo pravilo (kratki_rok, vague_kriterij, diskrim_uvjeti, …) dodaje se
kao funkcija dekorirana s `@don_rule(...)`. Registry se automatski popunjava
na import-u modula.

Pristup:
- Pravilo prima `ParsedItem` (parsed.text + parsed.metadata) i vraća
  `list[Finding]` — može bit prazna lista ako pravilo ne flaga ništa.
- Pravilo specificira na koje `item_kind` se primjenjuje (paragraph,
  requirement, criterion, list, table, deadline, …).
- Sve nalaze ide kroz `_enrich_findings_with_citations` u `mock.py` koji
  ih opcionalno obogati s realnim DKOM/ZJN citatima preko Qdrant retrieval-a.

Tipičan novi rule:

```python
@don_rule(
    name="kratki_rok",
    applies_to=("deadline",),
    description="Rok za dostavu ponude prekratak za vrstu postupka.",
)
def kratki_rok(item: ParsedItem) -> list[Finding]:
    text = item.text or ""
    days = _extract_days(text)  # custom util
    if days is not None and days < 15:
        return [{
            "kind": "kratki_rok",
            "status": AnalysisItemStatus.FAIL.value,
            "explanation": f"Rok od {days} dana je kraći od ZJN minimum-a (15).",
            "suggestion": "Produžiti rok na 15+ dana.",
            "is_mock": False,
            "citations": [],
        }]
    return []
```
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from src.document_parser.base import ParsedItem

logger = logging.getLogger(__name__)

# Finding format je dict (kompatibilan s mock.py postojećim findings-ima).
# Tipično polja: kind, status, explanation, suggestion, is_mock, citations.
Finding = dict[str, Any]
RuleFn = Callable[[ParsedItem], list[Finding]]


@dataclass
class RuleSpec:
    """Metadata pravila — koristi se za debug, audit, dokumentaciju."""
    name: str
    applies_to: tuple[str, ...]
    description: str
    fn: RuleFn


# Registry — popunjava se decorator-om
DON_RULES: list[RuleSpec] = []


def don_rule(
    *, name: str, applies_to: Iterable[str], description: str = ""
) -> Callable[[RuleFn], RuleFn]:
    """Decorator: registrira funkciju kao DON rule.

    Args:
        name: Jedinstveno ime pravila (npr. "brand_lock").
        applies_to: Lista item_kind-ova na koje se pravilo primjenjuje.
            Pravilo se preskače za ostale kindove.
        description: Što pravilo provjerava (za debug/audit).
    """

    def decorator(fn: RuleFn) -> RuleFn:
        spec = RuleSpec(
            name=name,
            applies_to=tuple(applies_to),
            description=description,
            fn=fn,
        )
        DON_RULES.append(spec)
        logger.debug("Registered DON rule: %s (applies_to=%s)", name, spec.applies_to)
        return fn

    return decorator


def run_don_rules(item: ParsedItem) -> list[Finding]:
    """Izvrši sva registrirana DON pravila nad item-om. Vrati spojenu
    listu nalaza (po redu registracije pravila).

    Ako pravilo baci exception, log-aj i nastavi — jedan loš rule ne smije
    rušiti cijelu analizu."""
    item_kind = (item.metadata or {}).get("kind", "")
    findings: list[Finding] = []
    for spec in DON_RULES:
        if item_kind not in spec.applies_to:
            continue
        try:
            result = spec.fn(item)
        except Exception:  # noqa: BLE001
            logger.exception("Rule %s exception, preskačem za item kind=%s", spec.name, item_kind)
            continue
        if result:
            findings.extend(result)
    return findings


# ---------------------------------------------------------------------------
# Konkretna pravila — započeto s brand_lock kao primjerom.
# `kratki_rok`, `vague_kriterij`, `diskrim_uvjeti` će se dodavati ovdje.

# Lazy import kako bismo izbjegli circular import s mock.py
def _brand_lock_impl(item: ParsedItem) -> list[Finding]:
    """Wrapper koji poziva postojeći `_detect_brand_mentions` iz mock.py.

    Brand_lock se već primjenjuje i na troškovnik kindove (stavka,
    opci_uvjeti, raw_text) direktno u `mock._build_findings` — ovdje je
    samo registriran za **DON kindove** kroz registry, da kad dođe
    refactor, oba puta vode kroz isto pravilo."""
    from src.api.schemas.analysis import AnalysisItemStatus
    from src.core.analyzer.mock import _PLACEHOLDER_ZJN, _detect_brand_mentions

    text = item.text or ""
    brand = _detect_brand_mentions(text)
    if brand is None:
        return []
    explanation, suggestion = brand
    return [
        {
            "kind": "brand_lock",
            "status": AnalysisItemStatus.FAIL.value,
            "explanation": explanation,
            "suggestion": suggestion,
            "is_mock": False,
            "citations": [dict(_PLACEHOLDER_ZJN)],
        }
    ]


don_rule(
    name="brand_lock",
    applies_to=("paragraph", "requirement", "criterion", "list", "table"),
    description=(
        "Specifikacija navodi marku/proizvođača bez klauzule 'ili jednakovrijedno'. "
        "ZJN čl. 207 traži neutralnost tehničke specifikacije."
    ),
)(_brand_lock_impl)
