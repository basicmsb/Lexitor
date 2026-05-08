from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sse_starlette.sse import EventSourceResponse

from src.api.deps import CurrentUser, DbSession
from src.api.schemas.analysis import (
    AnalysisDetail,
    AnalysisItemFeedbackUpdate,
    AnalysisItemPublic,
    AnalysisPublic,
    StartAnalysisResponse,
)
from src.core.analyzer import run_mock_analysis
from src.core.events import bus
from src.core.report import build_analysis_pdf
from src.models import Analysis, AnalysisItem, AnalysisStatus, Document, UserVerdict
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


@router.patch(
    "/analyses/{analysis_id}/items/{item_id}",
    response_model=AnalysisItemPublic,
)
async def update_item_feedback(
    analysis_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnalysisItemFeedbackUpdate,
    current_user: CurrentUser,
    session: DbSession,
) -> AnalysisItemPublic:
    """Persist user feedback (verdict + comment + include_in_pdf) on a
    single Lexitor finding. Used as autosave from the analysis card UI.
    Validates that user_comment is non-empty when verdict=incorrect."""
    stmt = (
        select(AnalysisItem)
        .where(AnalysisItem.id == item_id, AnalysisItem.analysis_id == analysis_id)
        .options(selectinload(AnalysisItem.citations))
    )
    result = await session.execute(stmt)
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Stavka nije pronađena."
        )

    # Authorisation — verify the analysis belongs to the user's project
    analysis = await session.get(Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Analiza nije pronađena."
        )
    document = await session.get(Document, analysis.document_id)
    if document is None or document.project_id != current_user.project_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Nemaš pristup analizi."
        )

    # Apply changes — only fields that the client included in payload
    if payload.clear_verdict:
        item.user_verdict = None
        item.user_comment = None
    else:
        if payload.user_verdict is not None:
            item.user_verdict = payload.user_verdict
        if payload.user_comment is not None:
            item.user_comment = payload.user_comment.strip() or None

    if payload.include_in_pdf is not None:
        item.include_in_pdf = payload.include_in_pdf

    # Validation: incorrect verdict requires a comment
    if (
        item.user_verdict == UserVerdict.INCORRECT
        and not (item.user_comment and item.user_comment.strip())
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Komentar je obavezan kad je nalaz označen kao pogrešan.",
        )

    await session.commit()
    await session.refresh(item, attribute_names=["citations"])
    return AnalysisItemPublic.model_validate(item)


@router.get(
    "/analyses/{analysis_id}/pdf",
    responses={200: {"content": {"application/pdf": {}}}},
)
async def export_analysis_pdf(
    analysis_id: uuid.UUID,
    session: DbSession,
    token: str = Query(..., description="Access token (browser link, no Authorization header)"),
    only_errors: bool = Query(False, description="Filter to FAIL/WARN/UNCERTAIN items only"),
) -> Response:
    """Generate a Lexitor-branded PDF export of the analysis. Browser
    `<a target='_blank' href='…?token=…'>` cannot set headers, so the
    access token comes through as a query parameter (mirrors the SSE
    stream pattern). `only_errors=true` filters out OK items."""
    try:
        payload = decode_token(token, expected_type="access")
        user_id = uuid.UUID(payload["sub"])
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Nevažeći token."
        ) from exc

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
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Analiza nije pronađena."
        )

    document = analysis.document
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nije pronađen."
        )

    # Authorisation — requesting user must belong to the analysis's project
    from src.models import User  # local import avoids circular at module load

    user = await session.get(User, user_id)
    if user is None or user.project_id != document.project_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Nemaš pristup analizi."
        )

    items_sorted = sorted(analysis.items, key=lambda it: it.position)
    # Load the requesting user's project so the PDF cover can show the
    # company logo / name alongside the Lexitor wordmark.
    from src.models import Project as ProjectModel  # local — avoid cycle

    project = await session.get(ProjectModel, user.project_id)
    pdf_bytes = build_analysis_pdf(
        analysis=analysis,
        items=items_sorted,
        document_filename=document.filename,
        only_errors=only_errors,
        project=project,
    )

    safe_name = document.filename.rsplit(".", 1)[0]
    filename = f"lexitor-{safe_name}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
