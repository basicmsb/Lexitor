from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sse_starlette.sse import EventSourceResponse

from src.api.deps import CurrentUser, DbSession
from src.api.schemas.analysis import (
    AnalysisDetail,
    AnalysisPublic,
    StartAnalysisResponse,
)
from src.core.analyzer import run_mock_analysis
from src.core.events import bus
from src.models import Analysis, AnalysisItem, AnalysisStatus, Document
from src.utils.security import decode_token

router = APIRouter(tags=["analyses"])


@router.post(
    "/documents/{document_id}/analyze",
    response_model=StartAnalysisResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_analysis(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    session: DbSession,
) -> StartAnalysisResponse:
    document = await session.get(Document, document_id)
    if document is None or document.project_id != current_user.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nije pronađen.")

    # If a recent (non-stale) analysis is already running for this doc,
    # return it instead of starting a duplicate. This guards against
    # React Strict Mode firing the bootstrap effect twice in dev.
    existing_stmt = (
        select(Analysis)
        .where(
            Analysis.document_id == document.id,
            Analysis.status.in_([AnalysisStatus.PENDING, AnalysisStatus.RUNNING]),
        )
        .order_by(Analysis.created_at.desc())
        .limit(1)
    )
    existing_result = await session.execute(existing_stmt)
    existing = existing_result.scalar_one_or_none()
    if existing is not None:
        return StartAnalysisResponse(
            analysis_id=existing.id,
            document_id=document.id,
            status=existing.status,
        )

    analysis = Analysis(document_id=document.id, status=AnalysisStatus.PENDING)
    session.add(analysis)
    await session.commit()
    await session.refresh(analysis)

    asyncio.create_task(run_mock_analysis(analysis.id))

    return StartAnalysisResponse(
        analysis_id=analysis.id,
        document_id=document.id,
        status=analysis.status,
    )


@router.get("/analyses/{analysis_id}", response_model=AnalysisDetail)
async def get_analysis(
    analysis_id: uuid.UUID,
    current_user: CurrentUser,
    session: DbSession,
) -> AnalysisDetail:
    stmt = (
        select(Analysis)
        .where(Analysis.id == analysis_id)
        .options(
            selectinload(Analysis.items).selectinload(AnalysisItem.citations),
            selectinload(Analysis.document),
        )
    )
    result = await session.execute(stmt)
    analysis = result.scalar_one_or_none()
    if analysis is None or analysis.document.project_id != current_user.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analiza nije pronađena.")
    return AnalysisDetail.model_validate(analysis)


@router.get("/analyses/{analysis_id}/stream")
async def stream_analysis(
    analysis_id: uuid.UUID,
    session: DbSession,
    token: str = Query(..., description="Access token (EventSource ne šalje Authorization header)"),
) -> EventSourceResponse:
    """SSE stream of analysis events.

    Browsers' `EventSource` API cannot set custom headers, so the access
    token must be passed as a query parameter. We validate it manually.
    """
    try:
        payload = decode_token(token, expected_type="access")
        user_id = uuid.UUID(payload["sub"])
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Nevažeći token.") from exc

    analysis = await session.get(Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analiza nije pronađena.")
    document = await session.get(Document, analysis.document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nije pronađen.")

    # Authorisation: requesting user must belong to the project that owns the analysis.
    from src.models import User  # local import to avoid circular at module load

    user = await session.get(User, user_id)
    if user is None or user.project_id != document.project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Nemaš pristup analizi.")

    queue = bus.subscribe(analysis_id)
    snapshot_status = analysis.status
    snapshot_summary = analysis.summary

    async def generator() -> AsyncIterator[dict[str, str]]:
        try:
            yield {
                "event": "snapshot",
                "data": json.dumps(
                    {
                        "type": "snapshot",
                        "analysis_id": str(analysis_id),
                        "status": snapshot_status.value,
                        "summary": snapshot_summary,
                    }
                ),
            }

            if snapshot_status in {AnalysisStatus.COMPLETE, AnalysisStatus.ERROR}:
                yield {
                    "event": "completed" if snapshot_status == AnalysisStatus.COMPLETE else "error",
                    "data": json.dumps(
                        {
                            "type": "completed" if snapshot_status == AnalysisStatus.COMPLETE else "error",
                            "analysis_id": str(analysis_id),
                            "summary": snapshot_summary,
                        }
                    ),
                }
                return

            while True:
                event = await asyncio.wait_for(queue.get(), timeout=300)
                yield {"event": event["type"], "data": json.dumps(event)}
                if event["type"] in {"completed", "error"}:
                    return
        except asyncio.TimeoutError:
            yield {"event": "timeout", "data": json.dumps({"type": "timeout"})}
        finally:
            bus.unsubscribe(analysis_id, queue)

    return EventSourceResponse(generator())


@router.get("/documents/{document_id}/analyses", response_model=list[AnalysisPublic])
async def list_document_analyses(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    session: DbSession,
) -> list[AnalysisPublic]:
    document = await session.get(Document, document_id)
    if document is None or document.project_id != current_user.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nije pronađen.")
    stmt = (
        select(Analysis)
        .where(Analysis.document_id == document_id)
        .order_by(Analysis.created_at.desc())
    )
    result = await session.execute(stmt)
    return [AnalysisPublic.model_validate(a) for a in result.scalars().all()]
