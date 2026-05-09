"""Export endpoint za označene primjere (training material za LLM prompt).

Vraća JSON sa svim stavkama u korisnikovom projektu koje imaju ručno
označavanje — bilo per-finding verdict (correct/incorrect) ili
ručno dodane nalaze (user_added_findings). To je ulazni materijal za
few-shot primjere u system prompt-u Smjera #1 (real LLM analyzer).

Filter `since` dopušta inkrementalni export — npr. samo stavke
ažurirane od zadnjeg labeling sessiona."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.api.deps import CurrentUser, DbSession
from src.models import Analysis, AnalysisItem, Document

router = APIRouter(tags=["labels"])


@router.get("/admin/export-labels")
async def export_labels(
    current_user: CurrentUser,
    session: DbSession,
    since: datetime | None = Query(
        None,
        description="Vrati samo stavke ažurirane od ovog datuma (ISO 8601).",
    ),
    document_id: uuid.UUID | None = Query(
        None,
        description="Filtriraj na jedan dokument (po želji).",
    ),
) -> dict[str, Any]:
    """Vraća JSON s označenim stavkama spremnima za korištenje kao
    few-shot primjeri u LLM promptu. Scope: korisnikov projekt."""

    stmt = (
        select(AnalysisItem)
        .join(Analysis, Analysis.id == AnalysisItem.analysis_id)
        .join(Document, Document.id == Analysis.document_id)
        .where(Document.project_id == current_user.project_id)
        .options(
            selectinload(AnalysisItem.citations),
            selectinload(AnalysisItem.analysis).selectinload(Analysis.document),
        )
    )

    if since is not None:
        stmt = stmt.where(AnalysisItem.updated_at >= since)
    if document_id is not None:
        stmt = stmt.where(Document.id == document_id)

    result = await session.execute(stmt)
    items = result.scalars().all()

    # Implicit acceptance pravilo (2026-05-09):
    # — explicit ✗ Pogrešno / ✓ Točno → user_verdict je postavljen
    # — + Dodaj nalaz → user_added_findings nije prazan
    # — bez ničeg → ako je dokument "aktivno označavan" (ima bar 1 stavku
    #   s eksplicitnim feedback-om), tretiramo kao implicit_correct
    #   (korisnik je vidio i prešao bez prigovora). Inače dokument još
    #   nije pregledan → ne ulazi u export.
    docs_with_activity: set[uuid.UUID] = {
        it.analysis.document_id
        for it in items
        if it.analysis is not None
        and (it.user_verdict is not None or bool(it.user_added_findings))
    }

    exported: list[dict[str, Any]] = []
    for it in items:
        document = it.analysis.document if it.analysis else None
        if document is None:
            continue
        if document.id not in docs_with_activity:
            continue  # dokument nije pregledan — preskoči

        has_verdict = it.user_verdict is not None
        has_added = bool(it.user_added_findings)
        has_la_findings = bool(it.findings)
        item_kind = (it.metadata_json or {}).get("kind")

        # Stavke bez ikakvog signala (no findings, no verdict, no added)
        # nisu informativne kao few-shot: LA nije ništa rekao, korisnik
        # nije ništa rekao. Prebacujemo samo ako ima bar jedan signal.
        # Iznimka: svi non-stavka kindovi (opci_uvjeti, recap, section_header)
        # ulaze samo ako imaju eksplicitan signal — automatska "uskladeno"
        # za section_header nije korisno za LLM.
        if not has_verdict and not has_added:
            if not has_la_findings:
                continue
            if item_kind not in ("stavka", "opci_uvjeti"):
                continue

        # Resolved verdict: explicit ako postoji, inače implicit_correct
        # kad LA ima nalaze ili je stavka (znači LA ništa nije našao i
        # korisnik se nije bunio).
        if has_verdict:
            resolved_verdict = it.user_verdict.value
            is_implicit = False
        elif has_la_findings or item_kind == "stavka":
            resolved_verdict = "correct"
            is_implicit = True
        else:
            resolved_verdict = None
            is_implicit = False

        exported.append(
            {
                "item_id": str(it.id),
                "analysis_id": str(it.analysis_id),
                "document_id": str(document.id),
                "document_filename": document.filename,
                "troskovnik_type": document.troskovnik_type.value,
                "position": it.position,
                "label": it.label,
                "kind": item_kind,
                "text": it.text,
                "metadata_json": it.metadata_json,
                "la_findings": it.findings or [],
                "la_status": it.status.value,
                "user_verdict": resolved_verdict,
                "is_implicit_verdict": is_implicit,
                "user_comment": it.user_comment,
                "include_in_pdf": it.include_in_pdf,
                "user_added_findings": it.user_added_findings or [],
                "updated_at": it.updated_at.isoformat() if it.updated_at else None,
            }
        )

    if not exported:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nema označenih primjera za export.",
        )

    return {
        "project_id": str(current_user.project_id),
        "exported_at": datetime.utcnow().isoformat(),
        "since": since.isoformat() if since else None,
        "count": len(exported),
        "items": exported,
    }
