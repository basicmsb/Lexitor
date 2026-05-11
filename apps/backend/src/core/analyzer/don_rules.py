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


# ---------------------------------------------------------------------------
# neprecizna_specifikacija — najveća kategorija u DKOM dataset-u (453 pojave,
# 48% uvazen rate). Deterministic detekcija ovdje hvata očite case-ove;
# suptilniji slučajevi će ići kroz LLM judge (Faza D).

import re  # noqa: E402

# Uska tolerancija — ±N% gdje je N <= 10
_NARROW_TOLERANCE_RE = re.compile(
    r"[±+\-]\s*(\d+(?:[.,]\d+)?)\s*%",
)

# Spomen specifične norme (ISO/EN/HRN/IEC + broj) BEZ "ili jednakovrijedno"
_NORM_REFERENCE_RE = re.compile(
    r"\b(ISO|EN|HRN|IEC|DIN|ASTM|ATEX)\s*"
    r"(?:EN\s*)?"  # može biti i "EN HRN EN" kombinacije
    r"\d{4,5}(?:[-:]\d+)?(?:\s*-?\s*\d{4})?",
    re.IGNORECASE,
)

# Riječi koje impliciraju ekskluzivnost (sume signala)
_EXCLUSIVE_TERMS = (
    # Eksplicitno "isključiv*"
    "isključiv",
    # Samo + bilo što (samo jedan, samo jedna, samo vodomjeri, samo proizvod)
    "samo jedan", "samo jedno", "samo jedna", "samo proizvod",
    "udovoljava samo", "omogućava samo", "omogucava samo", "omogućuje samo",
    "ispunjava samo", "udovoljiti samo",
    # Jedinstvenost
    "jedinog", "jedinstven", "jedinstvenog", "jedinstvenu",
    # Negacije
    "nijedan drugi", "ne postoji drugi", "ne postoji druga",
    "niti jedan drugi", "niti jedan", "ostali ne mogu",
    # Pogoduje
    "pogoduje isključivo", "pogoduje samo", "pogoduje jednom",
    # Nerealno / preuski
    "nerealan zahtjev", "neopravdano usk", "neopravdana sužav",
    "preuski", "preusko", "preuska",
    # Zatvaranje tržišta
    "ograničava tržišn", "sužava krug", "zatvara tržišt",
)

# Specifične fiksne dimenzije: AxBxC mm ili AxB mm (sumnjive ako su točne)
_FIXED_DIMENSIONS_RE = re.compile(
    r"\b\d{2,4}\s*[xX×]\s*\d{2,4}(?:\s*[xX×]\s*\d{2,4})?\s*mm\b",
)

# Vrlo specifična masa u kg s decimalom (npr. "7,8 kg" ili "7.8 kg")
_PRECISE_MASS_RE = re.compile(
    r"\b\d+[,.]\d+\s*kg\b",
)


def _check_narrow_tolerance(text: str) -> tuple[int, list[str]]:
    """Vrati (signal_count, primjeri) za uske tolerancije."""
    matches = []
    for m in _NARROW_TOLERANCE_RE.finditer(text):
        try:
            value = float(m.group(1).replace(",", "."))
            if value <= 10:
                matches.append(m.group(0))
        except ValueError:
            continue
    return len(matches), matches


def _check_norm_without_equivalent(text: str) -> tuple[int, list[str]]:
    """Vrati (signal_count, primjeri) za citate normi bez 'ili jednakovrijedno'."""
    text_lower = text.lower()
    if "jednakovrijed" in text_lower:
        return 0, []  # ima fallback klauzulu
    matches = [m.group(0) for m in _NORM_REFERENCE_RE.finditer(text)]
    return len(matches), matches[:3]


def _check_exclusive_terms(text: str) -> tuple[int, list[str]]:
    """Vrati (signal_count, primjeri) za ekskluzivne izraze."""
    text_lower = text.lower()
    hits = [term for term in _EXCLUSIVE_TERMS if term in text_lower]
    return len(hits), hits


def _check_fixed_dimensions(text: str) -> tuple[int, list[str]]:
    """Fiksne dimenzije BEZ tolerancije — vrlo specifične = sumnja."""
    dims = [m.group(0) for m in _FIXED_DIMENSIONS_RE.finditer(text)]
    if not dims:
        return 0, []
    # Ako u tekstu već ima ±N% tolerancije, dimenzije su vjerojatno OK
    if "±" in text or "+/-" in text.lower() or "tolerancij" in text.lower():
        return 0, []
    return len(dims), dims[:3]


def _neprecizna_specifikacija_impl(item: ParsedItem) -> list[Finding]:
    """Detektira tehničke specifikacije koje pogoduju jednom proizvođaču.

    Strategija: skupi signale (uska tolerancija, citat norme bez 'ili
    jednakovrijedno', ekskluzivni izrazi, fiksne dimenzije). 2+ signala
    = WARN, 3+ = FAIL (jaka indikacija). 1 signal nije dovoljan — može
    biti opravdano.

    DKOM citation per case (ZJN čl. 207, 209, 210, 280, 290) ide kroz
    `_enrich_findings_with_citations` u mock.py."""
    from src.api.schemas.analysis import AnalysisItemStatus

    text = item.text or ""
    if len(text) < 50:
        return []

    # Skupi sve signale
    signals = []  # list of (signal_type, count, examples)

    n, ex = _check_narrow_tolerance(text)
    if n > 0:
        signals.append(("uska_tolerancija", n, ex))

    n, ex = _check_norm_without_equivalent(text)
    if n > 0:
        # 2+ distinktnih normi bez jednakovrijedno = jaka indikacija (broji se
        # kao 2 signala umjesto 1)
        signals.append(("norma_bez_jednakovrijedno", n, ex))
        if n >= 2:
            signals.append(("multiple_norms", n, ex))

    n, ex = _check_exclusive_terms(text)
    if n > 0:
        signals.append(("ekskluzivni_izraz", n, ex))
        # 2+ ekskluzivnih izraza također jaka indikacija
        if n >= 2:
            signals.append(("multiple_exclusive", n, ex))

    n, ex = _check_fixed_dimensions(text)
    if n > 0:
        signals.append(("fiksne_dimenzije", n, ex))

    # 2+ signala = problem. 1 signal = vjerojatno OK.
    if len(signals) < 2:
        return []

    # Status: FAIL ako 3+ signala (jaka indikacija), inače WARN
    status = (
        AnalysisItemStatus.FAIL.value if len(signals) >= 3
        else AnalysisItemStatus.WARN.value
    )

    # Build explanation
    signal_labels = {
        "uska_tolerancija": "uska tolerancija",
        "norma_bez_jednakovrijedno": "specifična norma bez „ili jednakovrijedno”",
        "multiple_norms": "više normi bez „ili jednakovrijedno”",
        "ekskluzivni_izraz": "ekskluzivni izraz",
        "multiple_exclusive": "više ekskluzivnih izraza",
        "fiksne_dimenzije": "fiksne dimenzije bez raspona",
    }
    # Dedupliciraj signal-e istog tipa za prikaz (multiple_* ne mora biti
    # zaseban red u explanation-u)
    detail_parts = []
    seen_types = set()
    for sig_type, count, examples in signals:
        if sig_type.startswith("multiple_"):
            continue  # multiple_* je samo za scoring, ne za prikaz
        if sig_type in seen_types:
            continue
        seen_types.add(sig_type)
        label = signal_labels.get(sig_type, sig_type)
        ex_str = ", ".join(f"„{e}”" for e in examples[:2])
        detail_parts.append(f"• {label}: {ex_str}")

    explanation = (
        f"Specifikacija sadrži {len(signals)} signala koji upućuju na "
        f"mogući opis prilagođen jednom proizvođaču:\n"
        + "\n".join(detail_parts)
        + "\n\nZJN čl. 280 st. 4 i čl. 290 st. 1: tehničke specifikacije moraju "
        "biti dovoljno precizne da ponuditeljima omoguće utvrđivanje predmeta "
        "nabave, a istovremeno ne smiju neopravdano sužavati tržišnu utakmicu."
    )
    suggestion = (
        "Razmotri proširenje tolerancije, dopuni klauzulu „ili jednakovrijedno” "
        "uz norme, ili specificiraj kriterije objektivne usporedbe ako je "
        "ograničenje tehnički nužno."
    )

    return [
        {
            "kind": "neprecizna_specifikacija",
            "status": status,
            "explanation": explanation,
            "suggestion": suggestion,
            "is_mock": False,
            "citations": [],  # _enrich_findings_with_citations će dodati DKOM presedan
        }
    ]


don_rule(
    name="neprecizna_specifikacija",
    applies_to=("paragraph", "requirement", "list", "table"),
    description=(
        "Tehnička specifikacija je preuska i pogoduje jednom proizvođaču. "
        "Detektira: uske tolerancije (±N% za N≤10), specifične norme bez "
        "„ili jednakovrijedno”, ekskluzivne izraze, fiksne dimenzije. "
        "ZJN čl. 280 st. 4 i čl. 290 st. 1."
    ),
)(_neprecizna_specifikacija_impl)
