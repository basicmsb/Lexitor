from __future__ import annotations

import asyncio
import logging
import random
import re
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

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


_BRANDS = (
    # HVAC
    "Daikin", "Mitsubishi", "Toshiba", "Fujitsu", "Carrier", "Trane",
    "Helios", "Halton", "Systemair", "Vortice",
    # Sanitarna / armature
    "Geberit", "Grohe", "Hansgrohe", "Kludi", "Roca",
    # Odvodnja / cijevi
    "Aco", "Pipelife", "Wavin", "Rehau",
    # Građevinski
    "Knauf", "Sika", "Mapei", "Promat", "Ytong", "Wienerberger", "Roefix",
    "Baumit", "Velux", "Fibran", "Ursa", "Rockwool",
    # Elektro
    "Hilti", "Schneider", "Siemens", "ABB", "Hager", "Legrand", "Schiedel",
    # Premazi i alati
    "JUB", "Caparol", "Tikkurila", "Bosch", "Hilti",
)
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
) -> list[dict[str, Any]]:
    """Build citations for a flagged item.

    Cohere trial key is exhausted (1000 calls/month) — RAG retrieval is
    temporarily disabled so the analyzer doesn't stall ~138s per item on
    rate-limit retries. We fall back to the placeholder ZJN reference;
    real DKOM citations come back when we move to a paid key or run with
    Anthropic Citations.
    """
    if item_status == AnalysisItemStatus.OK:
        return []
    # item_text retained in signature for future RAG re-enable
    _ = item_text
    return [dict(_PLACEHOLDER_ZJN)]


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


def _serialize_item(item: AnalysisItem, citations: list[Citation]) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "position": item.position,
        "label": item.label,
        "text": item.text,
        "status": item.status.value,
        "explanation": item.explanation,
        "suggestion": item.suggestion,
        "metadata_json": item.metadata_json,
        "highlights": item.highlights,
        "citations": [
            {
                "id": str(c.id),
                "source": c.source.value,
                "reference": c.reference,
                "snippet": c.snippet,
                "url": c.url,
            }
            for c in citations
        ],
    }


async def _persist_item(
    session: AsyncSession,
    *,
    analysis_id: uuid.UUID,
    parsed: ParsedItem,
    status: AnalysisItemStatus,
    explanation: str | None,
    suggestion: str | None,
    citations: list[dict[str, Any]],
    highlights: list[dict[str, Any]],
) -> tuple[AnalysisItem, list[Citation]]:
    item = AnalysisItem(
        analysis_id=analysis_id,
        position=parsed.position,
        label=parsed.label,
        text=parsed.text,
        status=status,
        explanation=explanation,
        suggestion=suggestion,
        metadata_json=parsed.metadata or None,
        highlights=highlights or None,
    )
    session.add(item)
    await session.flush()

    citation_objs: list[Citation] = []
    for cit in citations:
        c = Citation(
            item_id=item.id,
            source=cit["source"],
            reference=cit["reference"],
            snippet=cit["snippet"],
            url=cit.get("url"),
        )
        session.add(c)
        citation_objs.append(c)
    await session.flush()
    return item, citation_objs


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

        for index, parsed_item in enumerate(parsed.items):
            await asyncio.sleep(random.uniform(0.15, 0.45))
            status = _pick_status()
            picked = _explanation_for(status, parsed_item.text)
            if picked is None:
                # Random reason was incompatible with the text (e.g. "brand
                # named" pick on text with no brand). Downgrade to OK rather
                # than fabricate a proizvođač that isn't there.
                status = AnalysisItemStatus.OK
                explanation, suggestion = None, None
            else:
                explanation, suggestion = picked
            citations = await _build_citations(status, parsed_item.text)
            highlights = _build_highlights(parsed_item.text, status)

            # Deterministic override: if the parser flagged any
            # arithmetic issue on this item, force FAIL + show the
            # actual problem instead of the random mock reasons.
            arithmetic = _detect_arithmetic_issues(parsed_item.metadata)
            if arithmetic is not None:
                problems, fix_suggestions = arithmetic
                status = AnalysisItemStatus.FAIL
                explanation = "Računska greška u stavci:\n" + "\n".join(
                    f"• {p}" for p in problems
                )
                suggestion = " ".join(fix_suggestions)
                citations = [dict(_PLACEHOLDER_ZJN)]

            # Group-sum validation: SUM formula must exist and cover all
            # math rows in its range. Drives status for kind="group_sum".
            group_sum = _detect_group_sum_issues(parsed_item.metadata)
            if group_sum is not None:
                gs_problems, gs_suggestions, gs_status = group_sum
                status = gs_status
                explanation = "Provjera UKUPNO retka:\n" + "\n".join(
                    f"• {p}" for p in gs_problems
                )
                suggestion = " ".join(gs_suggestions)
                citations = [dict(_PLACEHOLDER_ZJN)]
                highlights = []
            elif (
                parsed_item.metadata
                and parsed_item.metadata.get("kind") == "group_sum"
            ):
                # Group sum without issues — explicit OK with a friendly note.
                status = AnalysisItemStatus.OK
                explanation = (
                    f"SUM formula uredno pokriva svih "
                    f"{len(parsed_item.metadata.get('math_rows_in_range') or [])} "
                    f"matematičkih redova u rasponu."
                )
                suggestion = None
                citations = []
                highlights = []
            stored, stored_citations = await _persist_item(
                session,
                analysis_id=analysis_id,
                parsed=parsed_item,
                status=status,
                explanation=explanation,
                suggestion=suggestion,
                citations=citations,
                highlights=highlights,
            )
            summary[status.value] = summary.get(status.value, 0) + 1
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
