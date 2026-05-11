from __future__ import annotations

import asyncio
import logging
import random
import re
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.analyzer.rules import run_per_row_rules
from src.core.events import bus
from src.db.session import SessionLocal
from src.document_parser import parse_document
from src.document_parser.base import ParsedItem
from src.knowledge_base import search as knowledge_search
from src.models import (
    Analysis,
    AnalysisItem,
    AnalysisItemStatus,
    AnalysisStatus,
    Citation,
    CitationSource,
    Document,
    TroskovnikType,
)

logger = logging.getLogger(__name__)


_STATUS_WEIGHTS: list[tuple[AnalysisItemStatus, float]] = [
    (AnalysisItemStatus.OK, 0.78),
    (AnalysisItemStatus.WARN, 0.14),
    (AnalysisItemStatus.FAIL, 0.06),
    (AnalysisItemStatus.UNCERTAIN, 0.02),
]


_FAIL_REASONS = [
    (
        "Naveden je proizvod konkretnog proizvođača bez dodatka „ili jednakovrijedno”.",
        "Razmotriti dopunu opisa neutralnim parametrima i dodati klauzulu o jednakovrijednosti.",
    ),
    (
        "Tehnička specifikacija sužava krug ponuditelja na praktički jedinog proizvođača.",
        "Generalizirati opis ili razdvojiti stavku na više neutralnih pozicija.",
    ),
    (
        "Mjerna jedinica i opis stavke ne odgovaraju realnoj količini izvedbe.",
        "Provjeriti kalkulaciju i uskladiti s troškovničkim normativom.",
    ),
]


_WARN_REASONS = [
    (
        "Opis stavke nedovoljno specifičan za nedvosmislenu evaluaciju ponuda.",
        "Dodati ključne tehničke parametre (dimenzije, klasu, normu).",
    ),
    (
        "Količinski iznos odstupa od uobičajenog raspona za sličnu poziciju.",
        "Provjeriti količinu i jediničnu cijenu.",
    ),
]


def _pick_status() -> AnalysisItemStatus:
    rng = random.random()
    cumulative = 0.0
    for status, weight in _STATUS_WEIGHTS:
        cumulative += weight
        if rng < cumulative:
            return status
    return AnalysisItemStatus.OK


def _load_brands_from_json() -> tuple[str, ...]:
    """Učitaj brand listu iz `data/brands.json` (kurirano ručno).

    Korisnik dodaje nove brandove samo u JSON — bez code release-a.
    Vraća tuple imena brand-ova; redoslijed je iz JSON-a (zadržava
    semantičku grupiranost po kategorijama)."""
    import json
    from pathlib import Path
    candidates = [
        Path(__file__).resolve().parents[3] / "data" / "brands.json",
        Path("data/brands.json"),
    ]
    for path in candidates:
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                brands = data.get("brands") or []
                names = tuple(b["name"] for b in brands if isinstance(b, dict) and b.get("name"))
                if names:
                    logger.info("Učitano %d brandova iz %s", len(names), path)
                    return names
            except Exception:
                logger.exception("Neuspjelo čitanje brands.json — nastavljam s hardkodiranom listom")
    # Fallback ako data/brands.json ne postoji ili je prazan
    return (
        "Daikin", "Mitsubishi", "Geberit", "Grohe", "Hansgrohe",
        "Knauf", "Sika", "Mapei", "Ytong", "Baumit", "Velux",
        "Hilti", "Schneider", "Siemens", "ABB", "Hager", "Legrand",
        "JUB", "Caparol", "Bosch",
    )


_BRANDS = _load_brands_from_json()
_BRAND_RE = re.compile(
    r"\b(" + "|".join(re.escape(b) for b in _BRANDS) + r")\b",
    re.IGNORECASE,
)
# Phrases that signal brand-locked specifications even without naming
# the brand directly — analyzer flags the surrounding context.
_PHRASE_RE = re.compile(
    r"(?i)\b(?:proizvod(?:a)?\s+(?:tipa|kao)|tipa\s+kao|kao\s+npr\.?)\s+([\w\sčćžšđČĆŽŠĐ]{2,40}?)(?=[,.;:!?\n]|$)",
)


def _build_highlights(item_text: str, item_status: AnalysisItemStatus) -> list[dict[str, Any]]:
    if item_status == AnalysisItemStatus.OK:
        return []
    spans: list[dict[str, Any]] = []
    for m in _BRAND_RE.finditer(item_text):
        spans.append(
            {"start": m.start(), "end": m.end(), "label": "brand bez 'ili jednakovrijedno'", "kind": "brand"}
        )
    for m in _PHRASE_RE.finditer(item_text):
        spans.append(
            {"start": m.start(), "end": m.end(), "label": "marka navedena bez 'ili jednakovrijedno'", "kind": "phrase"}
        )
    # De-duplicate overlaps (keep earliest start, longest end)
    spans.sort(key=lambda s: (s["start"], -s["end"]))
    merged: list[dict[str, Any]] = []
    for s in spans:
        if merged and s["start"] < merged[-1]["end"]:
            continue
        merged.append(s)
    return merged


_PLACEHOLDER_ZJN = {
    "source": CitationSource.ZJN,
    "reference": "Članak 207. ZJN",
    "snippet": (
        "Kada se u tehničkoj specifikaciji upućuje na konkretnu marku, mora se "
        "dodati riječ „ili jednakovrijedno”."
    ),
    "url": "https://narodne-novine.nn.hr/clanci/sluzbeni/2016_12_120_2607.html",
}


async def _build_citations(
    item_status: AnalysisItemStatus,
    item_text: str,
    claim_type: str | None = None,
) -> list[dict[str, Any]]:
    """Build citations za flagged item kroz dual-search Qdrant RAG.

    Strategija:
    1. **Claim-level search** (`dkom_claims` collection) — najgranularniji,
       svaki hit je jedan argument žalitelja s DKOM verdiktom. Filtrira
       po claim_type ako je poznat (npr. "brand_lock") za relevantnost.
    2. **Fallback whole-decision search** (`dkom_decisions`) — ako claim
       search ne vrati dovoljno hit-ova, ili ako claim_type nije poznat.

    Production Cohere key (paid).
    """
    if item_status == AnalysisItemStatus.OK:
        return []
    if not item_text or not item_text.strip():
        return [dict(_PLACEHOLDER_ZJN)]
    try:
        from src.knowledge_base import search, search_claims

        citations: list[dict[str, Any]] = []
        query = item_text[:500]

        # 1. Claim-level — preferirano (strukturirano, s verdiktom)
        claim_hits = await search_claims(
            query, limit=3, claim_type=claim_type, only_uvazen=False,
        )
        citations.extend(_claim_hit_to_citation(h) for h in claim_hits)

        # 2. Ako nedovoljno claim hit-ova, dopuni whole-decision search-om
        if len(citations) < 3:
            chunk_hits = await search(query, limit=3 - len(citations))
            citations.extend(_hit_to_citation(h) for h in chunk_hits)

        return citations or [dict(_PLACEHOLDER_ZJN)]
    except Exception:  # noqa: BLE001 — RAG fail ne smije ubiti analizu
        logger.exception("RAG retrieval failed za item, koristim placeholder")
        return [dict(_PLACEHOLDER_ZJN)]


def _claim_hit_to_citation(hit: Any) -> dict[str, Any]:
    """Mapiranje ClaimHit → citation dict.

    Razlika od `_hit_to_citation`: ClaimHit ima strukturirane podatke
    (argument, obrazloženje, verdikt) — koristimo ih da napravimo bogatiji
    snippet i citaciju s DKOM kontekstom."""
    klasa = hit.klasa or ""
    snippet_parts = []
    if hit.dkom_obrazlozenje:
        verdict_marker = (
            "✓" if hit.dkom_verdict == "uvazen"
            else "✗" if hit.dkom_verdict == "odbijen"
            else "≈"
        )
        snippet_parts.append(f"{verdict_marker} {hit.dkom_obrazlozenje[:280]}")
    if hit.argument_zalitelja and len(snippet_parts) < 2:
        snippet_parts.append(f"Argument: {hit.argument_zalitelja[:200]}")
    snippet = "\n\n".join(snippet_parts)
    if len(snippet) > 600:
        snippet = snippet[:597] + "…"

    # Reference uključuje verdict + datum za jasniji kontekst
    reference = klasa
    if hit.datum_odluke:
        reference = f"{klasa} ({hit.datum_odluke})"

    return {
        "source": CitationSource.DKOM,
        "reference": reference,
        "snippet": snippet,
        "url": hit.pdf_url,
        "page": None,
    }


def _hit_to_citation(hit: Any) -> dict[str, Any]:
    """Mapiranje SearchHit → citation dict za FindingCitation schema.

    Razlikuje ZJN (klasa starts with 'ZJN') od DKOM odluka (UP/II-…)
    po prefiksu klasa polja. Dodaje #page=N fragment u URL ako PDF
    viewer podržava skok na stranicu (Chrome/Edge/Firefox za PDF.js)."""
    klasa = hit.klasa or ""
    klasa_lower = klasa.lower()
    if klasa.startswith("UP/"):
        source = CitationSource.DKOM
    elif (
        klasa.startswith("ZJN")
        or klasa_lower.startswith("pravilnik")
        or klasa_lower.startswith("zakon")
    ):
        # Sva hrvatska zakonska legislativa pod ZJN umbrellom u UI-u
        # (klasa tekst razlikuje: "ZJN čl. 207", "Pravilnik NN 65/2017 čl. 12",
        # "Zakon NN 18/2013 čl. 5", itd.)
        source = CitationSource.ZJN
    else:
        source = CitationSource.OTHER
    snippet = (hit.text or "").strip()
    if len(snippet) > 600:
        snippet = snippet[:597] + "…"
    page = hit.page
    url = hit.pdf_url
    if url and page:
        # browser PDF viewer: #page=N skače na traženu stranicu
        sep = "&" if "#" in url else "#"
        url = f"{url}{sep}page={page}"
    return {
        "source": source,
        "reference": klasa,
        "snippet": snippet,
        "url": url,
        "page": page,
    }


async def _enrich_findings_with_citations(
    findings: list[dict[str, Any]],
    item_text: str,
) -> None:
    """In-place: zamijeni placeholder citate u findings s realnim Qdrant
    hitsima. Per-finding citation set — različita pravila trebaju različite
    presedane (npr. brand_lock vs kratki_rok).

    Mapping finding.kind → DKOM claim_type za filtrirani search:
    - brand_lock → brand_lock claims (point-to-point match)
    - arithmetic, group_sum, recap_ref → no claim_type filter (math greška
      nije specifična kategorija u DKOM-u)
    - sve ostalo → no filter (LLM-judge će se dodati kasnije)
    """
    # Mapping naša finding.kind → DKOM claim_type (ako postoji semantička
    # korespondencija). None → fallback bez filtera.
    KIND_TO_CLAIM_TYPE = {
        "brand_lock": "brand_lock",
        # Buduća pravila:
        # "kratki_rok": "kratki_rok",
        # "vague_kriterij": "vague_kriterij",
        # "diskrim_uvjeti": "diskrim_uvjeti",
        # "neprecizna_spec": "neprecizna_specifikacija",
    }

    # Cache po claim_type — više finding-a istog tipa dijeli citaciju
    citation_cache: dict[str | None, list[dict[str, Any]]] = {}

    for f in findings:
        if f.get("status") not in ("warn", "fail", "uncertain"):
            continue
        if f.get("is_mock"):
            continue
        claim_type = KIND_TO_CLAIM_TYPE.get(f.get("kind", ""))
        if claim_type not in citation_cache:
            citation_cache[claim_type] = await _build_citations(
                AnalysisItemStatus.WARN, item_text, claim_type=claim_type,
            )
        if citation_cache[claim_type]:
            f["citations"] = citation_cache[claim_type]


def _explanation_for(
    status: AnalysisItemStatus,
    item_text: str = "",
) -> tuple[str | None, str | None] | None:
    """Pick a mock explanation/suggestion pair appropriate to `status`.

    Returns None when the random pick is incompatible with the actual
    text (e.g. a "brand mentioned" reason was chosen but no brand name
    or brand-locking phrase is present). The caller should treat that
    as "no real finding — downgrade to OK" rather than fabricating a
    proizvođač that isn't in the document."""
    if status == AnalysisItemStatus.OK:
        return None, None
    if status == AnalysisItemStatus.UNCERTAIN:
        return (
            "Stavku treba dodatno provjeriti — nije moguće sa sigurnošću utvrditi usklađenost.",
            None,
        )
    pool = _FAIL_REASONS if status == AnalysisItemStatus.FAIL else _WARN_REASONS
    explanation, suggestion = random.choice(pool)
    if _is_brand_reason(explanation) and not _text_has_brand_signal(item_text):
        # Random picker hallucinated a manufacturer that isn't in the
        # text. Refuse to lie — caller will downgrade this item to OK.
        return None
    return explanation, suggestion


_BRAND_REASON_RE = re.compile(
    r"proizvođač|proizvoda(č)?|jedinstvenog\s+proizvođača|sužava\s+krug",
    re.IGNORECASE,
)


def _is_brand_reason(explanation: str) -> bool:
    return bool(_BRAND_REASON_RE.search(explanation))


def _text_has_brand_signal(item_text: str) -> bool:
    if not item_text:
        return False
    if _BRAND_RE.search(item_text):
        return True
    if _PHRASE_RE.search(item_text):
        return True
    return False


_EQUIVALENT_RE = re.compile(
    # All Croatian forms of "jednakovrijedan" share the stem
    # "jednakovrijed" — masculine ("an"), feminine ("na"), neuter
    # ("no"), and inflected forms ("nu", "ne", "nih", "nim", "nom",
    # "noj", "nog", "nima") all follow. Match anywhere after "ili".
    r"\bili\s+jednakovrij?ed[a-zčćžšđ]{0,5}\b",
    re.IGNORECASE,
)


def _detect_brand_mentions(item_text: str) -> tuple[str, str] | None:
    """Deterministic brand check: if `item_text` names a manufacturer or
    contains a brand-locking phrase ("tipa kao", "kao npr.") without a
    nearby "ili jednakovrijedno" disclaimer, return (explanation,
    suggestion). Returns None when there's no brand signal or when
    "ili jednakovrijedno" already accompanies it.

    Used to flag brand mentions inside opci_uvjeti rows where stavka-style
    random mock doesn't apply but real brand-locking can still happen."""
    if not item_text:
        return None
    found: list[str] = []
    for m in _BRAND_RE.finditer(item_text):
        name = m.group(0)
        if name and name not in found:
            found.append(name)
    for m in _PHRASE_RE.finditer(item_text):
        captured = m.group(1).strip().rstrip(",.;:!?") if m.group(1) else ""
        if captured and captured not in found:
            found.append(captured)
    if not found:
        return None
    if _EQUIVALENT_RE.search(item_text):
        # Brand named, but with the "ili jednakovrijedno" clause — OK.
        return None
    brands_text = ", ".join(f"„{b}”" for b in found)
    explanation = (
        f"U tekstu je naveden proizvođač / marka {brands_text} bez dodatka "
        f"„ili jednakovrijedno”. ZJN članak 207. zahtijeva neutralnu "
        f"specifikaciju ili izričitu klauzulu o jednakovrijednosti."
    )
    suggestion = (
        "Razmotriti dopunu opisa neutralnim parametrima ili dodati "
        "klauzulu „ili jednakovrijedno”."
    )
    return explanation, suggestion


def _has_more_than_two_decimals(value: Any) -> bool:
    if value is None or value == "":
        return False
    try:
        n = float(value)
    except (TypeError, ValueError):
        return False
    cents = n * 100
    return abs(round(cents) - cents) > 0.005


def _format_eur(value: Any) -> str:
    if value is None or value == "":
        return "—"
    try:
        n = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " EUR"


def _detect_recap_line_issues(
    parsed_metadata: dict[str, Any] | None,
) -> tuple[list[str], list[str], AnalysisItemStatus] | None:
    """Validate a recap_line's cross-sheet references against the
    document-wide registry of UKUPNO rows. The parser pre-computed
    ref_validation entries; we just translate them to status + messages."""
    if not parsed_metadata or parsed_metadata.get("kind") != "recap_line":
        return None
    validation: list[dict[str, Any]] = parsed_metadata.get("ref_validation") or []
    if not validation:
        return None

    problems: list[str] = []
    suggestions: list[str] = []
    status = AnalysisItemStatus.OK

    for v in validation:
        v_status = v.get("validation_status")
        if v_status == "fail":
            problems.append(v.get("message", "Neispravna cross-sheet referenca."))
            status = AnalysisItemStatus.FAIL
        elif v_status == "warn":
            problems.append(v.get("message", "Neprepoznata referenca."))
            if status != AnalysisItemStatus.FAIL:
                status = AnalysisItemStatus.WARN

    if status == AnalysisItemStatus.OK:
        return None

    kinds = {v.get("validation_kind") for v in validation}
    if "math_row" in kinds:
        suggestions.append(
            "Promijeniti referencu da pokazuje na UKUPNO red odgovarajućeg "
            "sheeta umjesto na pojedinačnu math stavku."
        )
    if "missing_sheet" in kinds:
        suggestions.append(
            "Provjeriti naziv sheeta u formuli — sheet ne postoji ili je "
            "preimenovan."
        )
    if "unknown" in kinds:
        suggestions.append(
            "Provjeriti red u referenci — vjerojatno pokazuje na praznu "
            "ćeliju ili pomoćni red bez UKUPNO oznake."
        )

    return problems, suggestions, status


def _detect_group_sum_issues(
    parsed_metadata: dict[str, Any] | None,
) -> tuple[list[str], list[str], AnalysisItemStatus] | None:
    """Validate a group_sum item against the math rows it should aggregate.

    Returns (problems, suggestions, status) when issues are found, or
    None when the sum is complete and well-formed. Status is FAIL when
    the formula is missing entirely (hardcoded value), WARN when the
    SUM omits some math rows that fall in its range. Hierarchical
    rollups (sums-of-sums) are evaluated against the transitive leaf
    coverage so a correctly-rolled sum doesn't false-positive."""
    if not parsed_metadata or parsed_metadata.get("kind") != "group_sum":
        return None

    formula = parsed_metadata.get("formula")
    missing_rows: list[dict[str, Any]] = parsed_metadata.get("missing_rows") or []
    in_range: list[dict[str, Any]] = parsed_metadata.get("math_rows_in_range") or []
    is_rollup = bool(parsed_metadata.get("is_rollup"))

    problems: list[str] = []
    suggestions: list[str] = []
    status = AnalysisItemStatus.OK

    if not formula:
        problems.append(
            "U ćeliji UKUPNO nema SUM formule — iznos je upisan ručno, "
            "pa ne pratimo izvor zbroja."
        )
        suggestions.append(
            "Zamijeniti hardkodirani iznos formulom =SUM(...) koja pokriva sve "
            "stavke ove grupe."
        )
        status = AnalysisItemStatus.FAIL
        return problems, suggestions, status

    if missing_rows:
        rows_text = ", ".join(
            f"red {mr['row']}" + (f" ({mr['block_title']})" if mr.get("block_title") else "")
            for mr in missing_rows[:8]
        )
        more = "" if len(missing_rows) <= 8 else f" (+{len(missing_rows) - 8} dalje)"
        kind_word = "rollup-suma" if is_rollup else "Formula =SUM(...)"
        problems.append(
            f"{kind_word} ne pokriva {len(missing_rows)} matematičkih "
            f"redova koji upadaju u njezin raspon: {rows_text}{more}."
        )
        suggestions.append(
            "Proširiti SUM tako da uključi sve stavke (ili sve podgrupe) "
            "u rasponu — provjeriti i podgrupne UKUPNO retke ako postoje."
        )
        status = AnalysisItemStatus.WARN

    if not in_range:
        problems.append(
            "SUM formula referencira retke koji nisu prepoznati kao stavke "
            "(prazni redovi ili pomoćne ćelije)."
        )
        suggestions.append(
            "Provjeriti raspon SUM-a — vjerojatno pokazuje na pogrešne ćelije."
        )
        status = AnalysisItemStatus.WARN

    if not problems:
        return None
    return problems, suggestions, status


def _detect_arithmetic_issues(
    parsed_metadata: dict[str, Any] | None,
) -> tuple[list[str], list[str]] | None:
    """Walk math_rows and surface mismatches / over-precise totals.

    Returns (problems, suggestions) when any deterministic issue exists,
    or None when the rows look clean. The caller upgrades the item's
    status to FAIL and shows these strings on the analysis card."""
    if not parsed_metadata:
        return None
    rows = parsed_metadata.get("math_rows") or []
    if not rows:
        return None

    problems: list[str] = []
    suggestions: set[str] = set()

    for idx, row in enumerate(rows):
        excel = row.get("iznos")
        computed = row.get("computed_iznos")
        is_formula = bool(row.get("iznos_is_formula"))
        position = row.get("position_label")
        prefix = f"„{position}”" if position else f"red {idx + 1}"

        excel_num: float | None
        try:
            excel_num = float(excel) if excel not in (None, "") else None
        except (TypeError, ValueError):
            excel_num = None

        computed_num: float | None
        try:
            computed_num = float(computed) if computed not in (None, "") else None
        except (TypeError, ValueError):
            computed_num = None

        # Mismatch — Excel and Lexitor disagree (formula path is trusted)
        if (
            not is_formula
            and excel_num is not None
            and computed_num is not None
            and excel_num != computed_num
        ):
            delta = round(excel_num - computed_num, 2)
            problems.append(
                f"{prefix}: deklarirani iznos {_format_eur(excel_num)} ne odgovara "
                f"umnošku količine i jed. cijene ({_format_eur(computed_num)}). "
                f"Razlika {_format_eur(delta)}."
            )
            suggestions.add("Provjeriti formulu u stupcu Iznos i uskladiti deklarirani iznos s količinom × jediničnom cijenom.")
            continue

        # Over-precise total (>2 decimals) even when the values agree
        precision_value: float | None = None
        if excel_num is not None and _has_more_than_two_decimals(excel_num):
            precision_value = excel_num
        elif computed_num is not None and _has_more_than_two_decimals(computed_num):
            precision_value = computed_num
        if precision_value is not None:
            problems.append(
                f"{prefix}: iznos {precision_value} sadrži više od 2 decimale. "
                f"Novčani iznosi u EUR moraju biti zaokruženi na 2 decimale."
            )
            suggestions.add(
                "Zaokružiti jediničnu cijenu i iznos na 2 decimale; provjeriti zaokruživanja u formuli."
            )

    if not problems:
        return None
    return problems, sorted(suggestions)


def _enum_str(value: Any) -> Any:
    """Return Enum's .value when present, else fall through unchanged.
    Defensive helper for SA columns whose hydrated type may vary."""
    return value.value if hasattr(value, "value") else value


def _serialize_item(item: AnalysisItem, citations: list[Citation]) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "position": item.position,
        "label": item.label,
        "text": item.text,
        "status": _enum_str(item.status),
        "explanation": item.explanation,
        "suggestion": item.suggestion,
        "metadata_json": item.metadata_json,
        "highlights": item.highlights,
        "findings": item.findings,
        "user_verdict": _enum_str(item.user_verdict) if item.user_verdict else None,
        "user_comment": item.user_comment,
        "include_in_pdf": item.include_in_pdf,
        "citations": [
            {
                "id": str(c.id),
                "source": _enum_str(c.source),
                "reference": c.reference,
                "snippet": c.snippet,
                "url": c.url,
            }
            for c in citations
        ],
    }


# Severity rank for picking the worst finding as item-level status.
# Higher = more severe; OK is treated as 0 so any real finding wins.
_SEVERITY_RANK: dict[str, int] = {
    AnalysisItemStatus.OK.value: 0,
    AnalysisItemStatus.NEUTRAL.value: 0,
    AnalysisItemStatus.ACCEPTED.value: 1,
    AnalysisItemStatus.UNCERTAIN.value: 2,
    AnalysisItemStatus.WARN.value: 3,
    AnalysisItemStatus.FAIL.value: 4,
}


def _aggregate_status(findings: list[dict[str, Any]]) -> AnalysisItemStatus:
    """Item-level status = most severe finding's status. Used to drive
    the sidebar dot colour and summary counters."""
    if not findings:
        return AnalysisItemStatus.OK
    worst_value = max(
        (f.get("status") for f in findings),
        key=lambda s: _SEVERITY_RANK.get(s or "", 0),
    )
    try:
        return AnalysisItemStatus(worst_value)
    except ValueError:
        return AnalysisItemStatus.OK


async def _persist_item(
    session: AsyncSession,
    *,
    analysis_id: uuid.UUID,
    parsed: ParsedItem,
    findings: list[dict[str, Any]],
    highlights: list[dict[str, Any]],
) -> tuple[AnalysisItem, list[Citation]]:
    """Persist an item with its findings list. Item-level
    explanation/suggestion/status are derived from the highest-severity
    finding (legacy compat — frontend prefers the findings array)."""
    primary = findings[0] if findings else None
    aggregate = _aggregate_status(findings)
    # Naslovne stranice (kind="tekst") nisu ni "uskladeno" ni "warn" —
    # nisu uopće provjeravane. Forsiramo NEUTRAL da se u sidebar/tab
    # broju ne računaju kao zelene "uskladeno" stavke.
    if (parsed.metadata or {}).get("kind") == "tekst":
        aggregate = AnalysisItemStatus.NEUTRAL
    item = AnalysisItem(
        analysis_id=analysis_id,
        position=parsed.position,
        label=parsed.label,
        text=parsed.text,
        status=aggregate,
        explanation=primary.get("explanation") if primary else None,
        suggestion=primary.get("suggestion") if primary else None,
        metadata_json=parsed.metadata or None,
        highlights=highlights or None,
        findings=findings or None,
    )
    session.add(item)
    await session.flush()

    # Citations table is keyed to the item; we collapse all per-finding
    # citations onto the item for backward compat with the existing
    # `citations` relationship. Frontend reads finding.citations from
    # the JSONB list directly, so this is just for the legacy /pdf path.
    seen: set[tuple[str, str]] = set()
    citation_objs: list[Citation] = []
    for f in findings:
        for cit in f.get("citations") or []:
            key = (cit.get("source", ""), cit.get("reference", ""))
            if key in seen:
                continue
            seen.add(key)
            # Convert plain string source ("zjn"/"dkom"/…) to the
            # CitationSource enum so the SA Enum column hydrates a
            # real enum on read — otherwise c.source.value blows up
            # in serialization.
            raw_source = cit["source"]
            if isinstance(raw_source, CitationSource):
                src_enum = raw_source
            else:
                try:
                    src_enum = CitationSource(str(raw_source).lower())
                except ValueError:
                    src_enum = CitationSource.OTHER
            c = Citation(
                item_id=item.id,
                source=src_enum,
                reference=cit["reference"],
                snippet=cit.get("snippet") or "",
                url=cit.get("url"),
            )
            session.add(c)
            citation_objs.append(c)
    await session.flush()
    return item, citation_objs


def _build_findings(
    parsed_item: ParsedItem,
    troskovnik_type: TroskovnikType | None = None,
) -> list[dict[str, Any]]:
    """Run every deterministic rule + special-case detector on a parsed
    item and return the list of findings. Random demo mock is appended
    only when (a) the item is a free-text stavka, and (b) no real
    finding fired — so it never overshadows actual issues."""
    findings: list[dict[str, Any]] = []
    meta = parsed_item.metadata or {}
    item_kind = meta.get("kind", "stavka")
    text = parsed_item.text or ""

    # Naslovne stranice (kind="tekst") su isključivo informativne —
    # parser ih klasificira po imenu sheeta ("nasl", "naslovn",…).
    # Nema math, nema brand-locka, nema mock random WARN-ova. Vraćamo
    # praznu listu — analyzer će to spremiti kao OK item bez findings-a.
    if item_kind == "tekst":
        return findings

    # Per-row deterministic rules (missing JM/kol/cijena/opis, vague
    # description, zero unit price, etc.) apply ONLY to math-bearing
    # stavke. Opci_uvjeti, section headers and recap items skip these
    # — they're free-text rows where "Opis stavke je vrlo kratak" is a
    # nonsensical complaint. Only the brand-lock check below applies
    # to opci_uvjeti (and that's the only check Marko wants there
    # until DKOM-pattern analysis comes online).
    if item_kind == "stavka":
        findings.extend(run_per_row_rules(text, meta, troskovnik_type))

    # Troškovnik brand lock — primjenjuje se na troškovničke kindove
    # (stavka, opci_uvjeti, raw_text). DON kindovi (paragraph/requirement/
    # criterion/list/table) idu kroz `don_rules` registry niže.
    TROSKOVNIK_BRAND_LOCK_KINDS = ("stavka", "opci_uvjeti", "raw_text")
    if item_kind in TROSKOVNIK_BRAND_LOCK_KINDS:
        brand = _detect_brand_mentions(text)
        if brand is not None:
            brand_expl, brand_sugg = brand
            findings.append(
                {
                    "kind": "brand_lock",
                    "status": AnalysisItemStatus.FAIL.value,
                    "explanation": brand_expl,
                    "suggestion": brand_sugg,
                    "is_mock": False,
                    "citations": [dict(_PLACEHOLDER_ZJN)],
                }
            )

    # DON pravila — modularan registry (vidi `don_rules.py`).
    # Trenutno: brand_lock za DON kindove. Buduće: kratki_rok,
    # vague_kriterij, diskrim_uvjeti dodaju se ondje bez diranja ovog mjesta.
    from src.core.analyzer.don_rules import run_don_rules
    findings.extend(run_don_rules(parsed_item))

    # Arithmetic (kol×cijena ≠ iznos, or >2 decimals on money values)
    arith = _detect_arithmetic_issues(meta)
    if arith is not None:
        problems, fix_suggestions = arith
        findings.append(
            {
                "kind": "arithmetic",
                "status": AnalysisItemStatus.FAIL.value,
                "explanation": "Računska greška u stavci:\n"
                + "\n".join(f"• {p}" for p in problems),
                "suggestion": " ".join(fix_suggestions),
                "is_mock": False,
                "citations": [dict(_PLACEHOLDER_ZJN)],
            }
        )

    # Group-sum validation
    gs = _detect_group_sum_issues(meta)
    if gs is not None:
        gs_problems, gs_sugg, gs_status = gs
        findings.append(
            {
                "kind": "group_sum",
                "status": gs_status.value,
                "explanation": "Provjera UKUPNO retka:\n"
                + "\n".join(f"• {p}" for p in gs_problems),
                "suggestion": " ".join(gs_sugg),
                "is_mock": False,
                "citations": [dict(_PLACEHOLDER_ZJN)],
            }
        )
    elif item_kind == "group_sum":
        # Clean group sum — note as OK so the user sees a positive
        # confirmation rather than empty space.
        findings.append(
            {
                "kind": "group_sum_ok",
                "status": AnalysisItemStatus.OK.value,
                "explanation": (
                    "SUM formula uredno pokriva svih "
                    f"{len(meta.get('math_rows_in_range') or [])} "
                    "matematičkih redova u rasponu."
                ),
                "suggestion": None,
                "is_mock": False,
                "citations": [],
            }
        )

    # Recap-line cross-sheet ref validation
    rl = _detect_recap_line_issues(meta)
    if rl is not None:
        rl_problems, rl_sugg, rl_status = rl
        findings.append(
            {
                "kind": "recap_ref",
                "status": rl_status.value,
                "explanation": "Provjera reference:\n"
                + "\n".join(f"• {p}" for p in rl_problems),
                "suggestion": " ".join(rl_sugg) if rl_sugg else None,
                "is_mock": False,
                "citations": [dict(_PLACEHOLDER_ZJN)],
            }
        )
    elif item_kind == "recap_line" and meta.get("ref_validation"):
        refs_count = len(meta.get("ref_validation") or [])
        findings.append(
            {
                "kind": "recap_ref_ok",
                "status": AnalysisItemStatus.OK.value,
                "explanation": (
                    "Cross-sheet referenca uredno pokazuje na UKUPNO "
                    f"{'red' if refs_count == 1 else 'redove'} odgovarajućeg sheeta."
                ),
                "suggestion": None,
                "is_mock": False,
                "citations": [],
            }
        )

    # Random demo mock je BIO ovdje — uklonjen 2026-05-09 jer je trovao
    # labeling podatke (false positives koji nisu pravi nalazi). Ako stavka
    # nema nijedan real finding, to znači da algoritam ništa ne prijavljuje
    # i prikazuje se kao OK (zelena). Implicit acceptance pravilo (vidi
    # FeedbackControls): bez korisnikova klika računa se kao Točno.
    return findings


async def run_mock_analysis(analysis_id: uuid.UUID) -> None:
    """Background task: parse the document, emit fake item-by-item results."""
    async with SessionLocal() as session:
        analysis = await session.get(Analysis, analysis_id)
        if analysis is None:
            logger.warning("Analysis %s not found, aborting mock run", analysis_id)
            return
        document = await session.get(Document, analysis.document_id)
        if document is None:
            await _mark_failed(session, analysis, "Dokument nije pronađen.")
            return

        try:
            parsed = parse_document(__import__("pathlib").Path(document.storage_path))
        except Exception as exc:  # noqa: BLE001 — surface parser errors uniformly
            await _mark_failed(session, analysis, f"Parser greška: {exc}")
            return

        analysis.status = AnalysisStatus.RUNNING
        analysis.progress_percent = 0
        await session.commit()

        total = len(parsed.items)
        await bus.publish(
            analysis_id,
            {
                "type": "started",
                "analysis_id": str(analysis_id),
                "total": total,
                "metadata": parsed.metadata,
            },
        )

        summary = {
            "ok": 0,
            "warn": 0,
            "fail": 0,
            "neutral": 0,
            "accepted": 0,
            "uncertain": 0,
            "total": total,
        }

        troskovnik_type = document.troskovnik_type

        for index, parsed_item in enumerate(parsed.items):
            await asyncio.sleep(random.uniform(0.15, 0.45))
            findings = _build_findings(parsed_item, troskovnik_type)
            # Enrich findings sa real ZJN/DKOM citatima preko Qdrant retrieval-a
            await _enrich_findings_with_citations(
                findings, parsed_item.text or ""
            )
            highlights = _build_highlights(
                parsed_item.text, _aggregate_status(findings)
            )

            stored, stored_citations = await _persist_item(
                session,
                analysis_id=analysis_id,
                parsed=parsed_item,
                findings=findings,
                highlights=highlights,
            )
            status_key = _enum_str(stored.status)
            summary[status_key] = summary.get(status_key, 0) + 1
            analysis.progress_percent = int(((index + 1) / max(total, 1)) * 100)
            await session.commit()

            await bus.publish(
                analysis_id,
                {
                    "type": "item",
                    "analysis_id": str(analysis_id),
                    "item": _serialize_item(stored, stored_citations),
                    "progress": analysis.progress_percent,
                },
            )

        analysis.status = AnalysisStatus.COMPLETE
        analysis.progress_percent = 100
        analysis.summary = summary
        await session.commit()

        await bus.publish(
            analysis_id,
            {
                "type": "completed",
                "analysis_id": str(analysis_id),
                "summary": summary,
            },
        )


async def _mark_failed(session: AsyncSession, analysis: Analysis, message: str) -> None:
    analysis.status = AnalysisStatus.ERROR
    analysis.error_message = message
    await session.commit()
    await bus.publish(
        analysis.id,
        {"type": "error", "analysis_id": str(analysis.id), "error": message},
    )
