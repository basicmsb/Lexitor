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
    applies_to: tuple[str, ...]  # item kind (paragraph, requirement, …)
    applies_to_subtypes: tuple[str, ...] | None  # document subtype (None = sve)
    description: str
    fn: RuleFn


# Registry — popunjava se decorator-om
DON_RULES: list[RuleSpec] = []


def don_rule(
    *,
    name: str,
    applies_to: Iterable[str],
    description: str = "",
    applies_to_subtypes: Iterable[str] | None = None,
) -> Callable[[RuleFn], RuleFn]:
    """Decorator: registrira funkciju kao DON rule.

    Args:
        name: Jedinstveno ime pravila (npr. "brand_lock").
        applies_to: Lista item_kind-ova na koje se pravilo primjenjuje
            (paragraph, requirement, criterion, list, table, deadline, ...).
        applies_to_subtypes: Lista document_subtype vrijednosti na koje se
            pravilo primjenjuje. None znači "sve" (uključujući unknown).
            Ako je definirano, item s document_subtype koji nije u listi se
            preskače. Item BEZ subtype (legacy) uvijek prolazi.
        description: Što pravilo provjerava (za debug/audit).
    """

    def decorator(fn: RuleFn) -> RuleFn:
        spec = RuleSpec(
            name=name,
            applies_to=tuple(applies_to),
            applies_to_subtypes=(
                tuple(applies_to_subtypes) if applies_to_subtypes is not None else None
            ),
            description=description,
            fn=fn,
        )
        DON_RULES.append(spec)
        logger.debug(
            "Registered DON rule: %s (kinds=%s, subtypes=%s)",
            name, spec.applies_to, spec.applies_to_subtypes,
        )
        return fn

    return decorator


def run_don_rules(item: ParsedItem) -> list[Finding]:
    """Izvrši sva registrirana DON pravila nad item-om. Vrati spojenu
    listu nalaza (po redu registracije pravila).

    Filter logika:
    - item_kind mora biti u rule.applies_to (npr. paragraph, requirement, …)
    - document_subtype, ako postoji u item metadata, mora biti u
      rule.applies_to_subtypes ako je tamo definirano. Ako rule nema subtype
      filter, primjenjuje se na sve. Ako item nema subtype (None), pravilo
      se uvijek primjenjuje (legacy / nepoznato).

    Ako pravilo baci exception, log-aj i nastavi — jedan loš rule ne smije
    rušiti cijelu analizu."""
    meta = item.metadata or {}
    item_kind = meta.get("kind", "")
    item_subtype = meta.get("document_subtype")
    findings: list[Finding] = []
    for spec in DON_RULES:
        if item_kind not in spec.applies_to:
            continue
        # Subtype filter (samo ako rule deklarira ograničenje I item ima subtype)
        if spec.applies_to_subtypes is not None and item_subtype is not None:
            if item_subtype not in spec.applies_to_subtypes:
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
    applies_to_subtypes=(
        # Brand mention je realan problem u: tehničke specifikacije,
        # troškovnik, upute (gdje se opisuje predmet). NE u kriterijima
        # subjekta/ponude (tu su uvjeti ponuditelja, ne specifikacija predmeta)
        # NE u općim podacima, prijedlogu ugovora.
        "tehnicke_specifikacije", "troskovnik", "upute_ponuditeljima", "ostalo",
    ),
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
    applies_to_subtypes=(
        # Neprecizna specifikacija se događa u: tehničke specifikacije,
        # troškovnik. NE u kriterijima ponuditeljima ili općim podacima.
        "tehnicke_specifikacije", "troskovnik", "upute_ponuditeljima",
    ),
    description=(
        "Tehnička specifikacija je preuska i pogoduje jednom proizvođaču. "
        "Detektira: uske tolerancije (±N% za N≤10), specifične norme bez "
        "„ili jednakovrijedno”, ekskluzivne izraze, fiksne dimenzije. "
        "ZJN čl. 280 st. 4 i čl. 290 st. 1."
    ),
)(_neprecizna_specifikacija_impl)


# ---------------------------------------------------------------------------
# kratki_rok — 13 pojava u dataset-u (manja kategorija, ali deterministic).
# ZJN čl. 219-220: minimum 30 dana za otvoreni postupak (nadvrijednosni),
# 15 dana za skraćeni. Lexitor je strogi — sve < 15 dana flagga.

_DEADLINE_DAYS_RE = re.compile(
    r"\brok(?:u|om)?\s+(?:od|za)\s+(\d{1,3})\s+dan",
    re.IGNORECASE,
)

# Rečenica MORA sadržavati ovu kombinaciju: "ponud*" + jedna od dostavnih riječi.
_PONUDA_RE = re.compile(r"\bponud[aeiu]\b", re.IGNORECASE)
_DOSTAVA_VERB_RE = re.compile(
    r"\b(?:dostav|podnoš|preda[jt][ie]|primanj|primit)",
    re.IGNORECASE,
)

# Rečenica NE smije sadržavati ove riječi (rok nije za dostavu ponude nego nešto drugo).
_NOT_DOSTAVA_ANTI = re.compile(
    r"\b(?:produžen|produzen|valjanost|valjan\w*\s+(?:ponud|jamst)|"
    r"garancij|jamstv|potpisivanj|izvedb|izvršen|izvrsen|izvođen|izvodjen|"
    r"ugovor|isporuk|ispostavlj|otklanjan|popravak|reklamacij|provjer)",
    re.IGNORECASE,
)


def _find_sentence_around(text: str, position: int) -> str:
    """Vrati rečenicu (između . ! ? ili newline) koja sadrži zadanu poziciju."""
    # Granice prema natrag
    start = position
    while start > 0:
        ch = text[start - 1]
        if ch in ".!?\n":
            break
        start -= 1
    # Granice prema naprijed
    end = position
    while end < len(text):
        ch = text[end]
        if ch in ".!?\n":
            break
        end += 1
    return text[start:end]

_SHORT_DEADLINE_TERMS = (
    "kratko vrijem",
    "kratak rok",
    "kratki period",
    "kraći period",
    "kraći rok",
    "skraćeni period",
    "neopravdano kratak",
    "neopravdano kratko",
    "minimalni zakonski rok",
    "minimalni rok",
    "nedovoljno vremena",
    "tehnički nemoguć",
    "tehnicki nemoguc",
    "ne stiže se",
    "ne stiže",
    "ne stize",
    "preostalom roku",
    "preostalo vrijem",
    "preostali rok",
    "prekratak rok",
    "prekratko vrijem",
    "kako bi ostavio",
    "kako bi sprijeci",
    "kako bi onemogući",
    "kako bi onemogu",
    "namjerno kratak",
    "namjerno kratko",
)

_NO_EXTENSION_TERMS = (
    "nije odredio novi rok",
    "nije produljio rok",
    "nije produžio rok",
    "nije produzio rok",
    "izmjena bez produljen",
    "izmjena bez produzen",
    "bez produljenja roka",
    "bez produženja roka",
    "bez produzenja roka",
)


def _kratki_rok_impl(item: ParsedItem) -> list[Finding]:
    """Detektira premali rok za dostavu ponude.

    Strategija:
    - Eksplicitan broj dana < 15 → WARN (ispod ZJN čl. 219 minimuma)
    - Eksplicitan broj dana < 7 → FAIL (sigurno krši svaki minimum)
    - 2+ signala suspicious context → WARN
    """
    from src.api.schemas.analysis import AnalysisItemStatus

    text = item.text or ""
    if len(text) < 30:
        return []

    text_lower = text.lower()

    signals: list[tuple[str, str]] = []  # (signal_type, detail)

    # 1. Eksplicitan kratki rok (broj dana) — strogi rečenični kontekst
    # Pravilo se aktivira SAMO ako rečenica oko match-a:
    # - sadrži "ponuda" (any form)
    # - sadrži dostavni glagol ("dostav", "podnoš", "preda*", "primanj")
    # - NE sadrži anti-riječi ("produžen", "valjanost", "garancij", "ugovor"
    #   "izvedb", "potpisivanj" — to su rokovi za druge stvari, ne ponudu)
    explicit_short_days: int | None = None
    for m in _DEADLINE_DAYS_RE.finditer(text):
        try:
            days = int(m.group(1))
        except ValueError:
            continue
        # Pronađi rečenicu koja sadrži match
        sentence = _find_sentence_around(text, m.start())
        # Mora biti o dostavi ponude
        if not _PONUDA_RE.search(sentence):
            continue
        if not _DOSTAVA_VERB_RE.search(sentence):
            continue
        # Ne smije biti o produženju/valjanosti/garanciji/ugovoru/izvedbi
        if _NOT_DOSTAVA_ANTI.search(sentence):
            continue
        if days < 15:
            signals.append((
                "kratak_eksplicitni_rok",
                f"rok od {days} dana za dostavu ponude",
            ))
            if explicit_short_days is None or days < explicit_short_days:
                explicit_short_days = days

    # 2. Suspicious context terms
    for term in _SHORT_DEADLINE_TERMS:
        if term in text_lower:
            signals.append(("kontekst_kratkog_roka", term))

    # 3. No extension after change
    for term in _NO_EXTENSION_TERMS:
        if term in text_lower:
            signals.append(("bez_produljenja_nakon_izmjene", term))

    if not signals:
        return []

    # Status logika:
    # - eksplicitni < 7 dana → FAIL
    # - eksplicitni < 15 dana → WARN (bez obzira broj drugih signala)
    # - 2+ signala konteksta → WARN
    # - 1 signal samo → INFO/neutral (premali signal, vraćamo prazno)
    if explicit_short_days is not None and explicit_short_days < 7:
        status = AnalysisItemStatus.FAIL.value
    elif explicit_short_days is not None and explicit_short_days < 15:
        status = AnalysisItemStatus.WARN.value
    elif len(signals) >= 2:
        status = AnalysisItemStatus.WARN.value
    else:
        return []  # 1 signal bez eksplicitnog broja nije dovoljno

    # Build explanation
    detail_parts = []
    seen_types = set()
    for sig_type, detail in signals:
        if sig_type in seen_types:
            continue
        seen_types.add(sig_type)
        label = {
            "kratak_eksplicitni_rok": "kratak eksplicitni rok",
            "kontekst_kratkog_roka": "kontekst kratkog roka",
            "bez_produljenja_nakon_izmjene": "nije produljen rok nakon izmjena",
        }.get(sig_type, sig_type)
        detail_parts.append(f"• {label}: „{detail}”")

    explanation = (
        "Detektirani signali koji ukazuju na prekratak rok za pripremu "
        "ponude:\n"
        + "\n".join(detail_parts)
        + "\n\nZJN čl. 219 propisuje minimum 30 dana za otvoreni postupak "
        "(nadvrijednosno) ili 15 dana za skraćeni postupak. Kratki rokovi "
        "diskriminiraju ponuditelje koji nemaju pre-existing ponudu spremnu."
    )
    suggestion = (
        "Produži rok za dostavu ponude na najmanje 15 dana (skraćeni) odnosno "
        "30 dana (standard za otvoreni postupak). Ako su učinjene značajne "
        "izmjene dokumentacije, obvezno odrediti novi (produljeni) rok."
    )

    return [
        {
            "kind": "kratki_rok",
            "status": status,
            "explanation": explanation,
            "suggestion": suggestion,
            "is_mock": False,
            "citations": [],  # _enrich_findings_with_citations će dodati DKOM presedan
        }
    ]


don_rule(
    name="kratki_rok",
    applies_to=("paragraph", "requirement", "deadline", "list"),
    applies_to_subtypes=(
        # Rok za dostavu ponude se navodi u: opći podaci, upute ponuditeljima.
        # Ne u tehničkim specifikacijama / troškovniku / kriterijima.
        "opci_podaci", "upute_ponuditeljima",
    ),
    description=(
        "Rok za dostavu ponude je prekratak. ZJN čl. 219: minimum 30 dana "
        "otvoreni, 15 dana skraćeni. Detektira eksplicitan broj dana + "
        "kontekstualne signale (kratko vrijeme, neproduljenje nakon izmjene)."
    ),
)(_kratki_rok_impl)


# ---------------------------------------------------------------------------
# diskrim_uvjeti — uvjeti sposobnosti koji isključuju većinu ponuditelja
# (ZJN čl. 256-272). 116 pojava u DKOM dataset-u, 38% uvazen rate.
# Konzervativna detekcija — više signala potrebno zbog rizika false positive.

# Godine iskustva — "N godina" u kontekstu iskustva, gdje je N visok
_YEARS_EXPERIENCE_RE = re.compile(
    r"\b(\d+)\s*\+?\s*godin[ae]?\s+(?:isk|rad|prak|stru[čc])",
    re.IGNORECASE,
)

# Tuzemne komore / HR-only uvjeti (ograničavaju EU subjekte) — sve padežne varijante
_HR_LIMITING_TERMS = (
    "hrvatska komora",
    "hrvatske komore",
    "hrvatskoj komori",
    "hrvatsku komoru",
    "hrvatskom komorom",
    "hkis",  # Hrvatska komora inženjera strojarstva — kratica
    "hkig",  # građevinarstva
    "hkae",  # arhitekata
    "tuzemnoj",
    "tuzemnog",
    "tuzemnih",
    "tuzemski",
    "tuzemne",
    "tuzemni propis",
    "samo u rh",
    "samo u hrvatskoj",
    "registrira u rh",
    "sjedište u rh",
    "sjedište u hrvatskoj",
)

# Specifični certifikati / ovlaštenja koje malo tko ima
_RESTRICTIVE_CERT_TERMS = (
    "ovjerenu potvrdu proizvođača",
    "ovjerenu izjavu proizvođača",
    "ovjerenu potvrdu proizvodjaca",
    "ovjerenu izjavu proizvodjaca",
    "ovlaštenje proizvođača",
    "ovlast proizvođača",
    "ovlas. proizvod",
    "ovlašteni distributer",
    "ovlasteni distributer",
    "ekskluzivni distributer",
    "potvrda hakom",
    "potvrdu hakom",
    "potvrdu hakom-a",
    "potvrda agencije",
)

# Vlastiti pogon / servis / oprema (često stroga eliminacija) — sve padežne
_OWN_RESOURCES_TERMS = (
    "vlastiti pogon", "vlastitog pogona", "vlastitim pogonom", "vlastitom pogonu",
    "vlastiti servis", "vlastitog servisa", "vlastitim servisom",
    "vlastita oprema", "vlastite opreme", "vlastitu opremu", "vlastitom opremom",
    "vlastita mreža", "vlastite mreže", "vlastitom mrežom",
    "vlastiti laboratorij", "vlastitim laboratorij",
    "vlastiti sustav", "vlastitim sustavom",
    "u vlasništvu ponuditelj",
    "raspolaganje vlastit",
)

# Eksplicitni izrazi koje DKOM već koristi kao indikatore
_DISCRIM_INDICATOR_TERMS = (
    "diskrim",
    "isključuje",
    "isključuju",
    "iskljucuje",
    "onemogu",
    "ne mogu sudjelov",
    "prepuska prag",
    "prestrog",
    "nadmašuje",
    "prekorač",
    "neopravdano usk",
    "nemoguće zadovolj",
    "nemoguce zadovolj",
    "ograničava tržišn",
)

# Min N referenci/projekata
_REFERENCES_COUNT_RE = re.compile(
    r"\b(?:najmanje|minimum|minimalno|min\.?|barem|najmanj)\s+(\d+)\s+(?:izvedenih\s+)?(?:referenc|projek|ugovor|isporuk|usl|posl)",
    re.IGNORECASE,
)


def _check_years_experience(text: str) -> tuple[int, list[str]]:
    """Detektiraj zahtjeve >= 7 godina iskustva (sumnjivo)."""
    matches = []
    for m in _YEARS_EXPERIENCE_RE.finditer(text):
        try:
            years = int(m.group(1))
            if years >= 7:
                matches.append(f"{years} godina iskustva")
        except ValueError:
            continue
    return len(matches), matches


def _check_term_list(text_lower: str, terms: tuple[str, ...]) -> tuple[int, list[str]]:
    hits = [t for t in terms if t in text_lower]
    return len(hits), hits


def _check_references_count(text: str) -> tuple[int, list[str]]:
    """Detektiraj min N referenci/projekata gdje N >= 5."""
    matches = []
    for m in _REFERENCES_COUNT_RE.finditer(text):
        try:
            n = int(m.group(1))
            if n >= 5:
                matches.append(m.group(0))
        except ValueError:
            continue
    return len(matches), matches


def _diskrim_uvjeti_impl(item: ParsedItem) -> list[Finding]:
    """Detektira uvjete sposobnosti koji diskriminiraju ponuditelje.

    Strategija: skupljanje signala. Konzervativan — 2+ signala = WARN,
    3+ = FAIL. Mnogi pojedinačni uvjeti su opravdani (godine iskustva za
    sloveniju, certifikat za telekom...), pa flag samo kad više pattern-a
    ukazuje na sistematsku diskriminaciju.
    """
    from src.api.schemas.analysis import AnalysisItemStatus

    text = item.text or ""
    if len(text) < 50:
        return []

    text_lower = text.lower()

    signals: list[tuple[str, list[str]]] = []

    n, ex = _check_years_experience(text)
    if n > 0:
        signals.append(("godine_iskustva", ex))
        # ≥10 godina je jaka indikacija — broji se kao 2 signala
        for e in ex:
            try:
                yrs = int(e.split()[0])
                if yrs >= 10:
                    signals.append(("godine_iskustva_visoke", [e]))
                    break
            except (ValueError, IndexError):
                continue

    n, ex = _check_term_list(text_lower, _HR_LIMITING_TERMS)
    if n > 0:
        signals.append(("hr_ograničenje", ex))
        # Tuzemne komore su strog signal sam po sebi
        if any("komor" in t or "tuzemn" in t for t in ex):
            signals.append(("hr_strong_signal", ex))

    n, ex = _check_term_list(text_lower, _RESTRICTIVE_CERT_TERMS)
    if n > 0:
        signals.append(("restriktivni_certifikat", ex))

    n, ex = _check_term_list(text_lower, _OWN_RESOURCES_TERMS)
    if n > 0:
        signals.append(("vlastiti_resursi", ex))

    n, ex = _check_term_list(text_lower, _DISCRIM_INDICATOR_TERMS)
    if n > 0:
        signals.append(("diskriminacijski_izraz", ex))

    n, ex = _check_references_count(text)
    if n > 0:
        signals.append(("velik_broj_referenci", ex))

    if len(signals) < 2:
        return []

    # 3+ signala = FAIL (jaka indikacija), 2 signala = WARN
    status = (
        AnalysisItemStatus.FAIL.value if len(signals) >= 3
        else AnalysisItemStatus.WARN.value
    )

    signal_labels = {
        "godine_iskustva": "visoki broj godina iskustva (≥7)",
        "godine_iskustva_visoke": None,  # skip — included in godine_iskustva
        "hr_ograničenje": "ograničenje na hrvatske subjekte",
        "hr_strong_signal": None,  # skip
        "restriktivni_certifikat": "ovlaštenje/potvrda specifičnog izvora",
        "vlastiti_resursi": "vlastiti pogon/servis/oprema",
        "diskriminacijski_izraz": "izraz diskriminacijske prirode",
        "velik_broj_referenci": "min. 5+ referenci/projekata",
    }
    detail_parts = []
    seen = set()
    for sig_type, examples in signals:
        if sig_type in seen:
            continue
        label = signal_labels.get(sig_type, sig_type)
        if label is None:
            continue  # internal signal, ne za prikaz
        seen.add(sig_type)
        ex_str = ", ".join(f"„{e}”" for e in examples[:2])
        detail_parts.append(f"• {label}: {ex_str}")

    explanation = (
        f"Detektirani signali ({len(signals)}) koji upućuju na diskriminatorne "
        f"uvjete sposobnosti:\n"
        + "\n".join(detail_parts)
        + "\n\nZJN čl. 256-272 traži da uvjeti sposobnosti budu razmjerni "
        "predmetu nabave i ne smiju neopravdano isključivati ponuditelje. "
        "Posebno pažljivo s ograničavanjem na tuzemne komore (EU sloboda "
        "kretanja) i s pretjeranim godinama iskustva."
    )
    suggestion = (
        "Provjeri da su uvjeti razmjerni predmetu nabave. Razmotri: "
        "(1) prihvaćanje EU komora paralelno s hrvatskom, "
        "(2) smanjenje minimuma godina iskustva ako predmet to dopušta, "
        "(3) prihvaćanje jednakovrijednih dokaza umjesto specifičnih potvrda."
    )

    return [
        {
            "kind": "diskrim_uvjeti",
            "status": status,
            "explanation": explanation,
            "suggestion": suggestion,
            "is_mock": False,
            "citations": [],  # auto-enrichment
        }
    ]


don_rule(
    name="diskrim_uvjeti",
    applies_to=("paragraph", "requirement", "criterion", "list"),
    applies_to_subtypes=(
        # Diskriminatorni uvjeti sposobnosti su STRIKTNO problem KRITERIJA
        # za odabir ponuditelja. NIJE problem u tehničkim specifikacijama
        # (tu projektant često navodi 'ovlašteni inženjer elektrotehnike,
        # Hrvatska komora' kao SVOJU referenciju — to je info o autoru,
        # ne kriterij za ponuditelje).
        "kriteriji_subjekta", "kriteriji_ponude", "upute_ponuditeljima",
    ),
    description=(
        "Uvjeti sposobnosti (financijska, tehnička, stručna) koji neopravdano "
        "isključuju ponuditelje. Multi-signal: godine iskustva, tuzemne komore, "
        "restriktivni certifikati, vlastiti resursi. ZJN čl. 256-272."
    ),
)(_diskrim_uvjeti_impl)
