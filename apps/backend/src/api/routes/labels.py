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

    exported: list[dict[str, Any]] = []
    for it in items:
        has_verdict = it.user_verdict is not None
        has_added = bool(it.user_added_findings)
        if not has_verdict and not has_added:
            continue  # ne-označeno → preskoči

        document = it.analysis.document if it.analysis else None
        exported.append(
            {
                "item_id": str(it.id),
                "analysis_id": str(it.analysis_id),
                "document_id": str(document.id) if document else None,
                "document_filename": document.filename if document else None,
                "position": it.position,
                "label": it.label,
                "kind": (it.metadata_json or {}).get("kind"),
                "text": it.text,
                "metadata_json": it.metadata_json,
                "la_findings": it.findings or [],
                "la_status": it.status.value,
                "user_verdict": it.user_verdict.value if it.user_verdict else None,
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
