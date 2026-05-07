from __future__ import annotations

import asyncio
import logging
import random
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


def _explanation_for(status: AnalysisItemStatus) -> tuple[str | None, str | None]:
    if status == AnalysisItemStatus.OK:
        return None, None
    if status == AnalysisItemStatus.FAIL:
        return random.choice(_FAIL_REASONS)
    if status == AnalysisItemStatus.WARN:
        return random.choice(_WARN_REASONS)
    return (
        "Stavku treba dodatno provjeriti — nije moguće sa sigurnošću utvrditi usklađenost.",
        None,
    )


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
            explanation, suggestion = _explanation_for(status)
            citations = await _build_citations(status, parsed_item.text)
            stored, stored_citations = await _persist_item(
                session,
                analysis_id=analysis_id,
                parsed=parsed_item,
                status=status,
                explanation=explanation,
                suggestion=suggestion,
                citations=citations,
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
