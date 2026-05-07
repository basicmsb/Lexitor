from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from src.api.deps import CurrentUser
from src.api.schemas.knowledge import (
    IndexedSource,
    SearchHitPublic,
    SearchRequest,
    SearchResponse,
    SourcesResponse,
)
from src.knowledge_base import list_indexed_sources, search

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("/search", response_model=SearchResponse)
async def search_knowledge(
    payload: SearchRequest,
    current_user: CurrentUser,  # noqa: ARG001
) -> SearchResponse:
    try:
        hits = await search(
            payload.query,
            limit=payload.limit,
            year=payload.year,
            source=payload.source,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Pretraga nedostupna: {exc}",
        ) from exc

    return SearchResponse(
        query=payload.query,
        hits=[
            SearchHitPublic(
                klasa=h.klasa,
                predmet=h.predmet,
                page=h.page,
                chunk_index=h.chunk_index,
                text=h.text,
                score=h.score,
                pdf_url=h.pdf_url,
                odluka_datum=h.odluka_datum,
                year=h.year,
            )
            for h in hits
        ],
    )


@router.get("/sources", response_model=SourcesResponse)
async def list_sources(
    current_user: CurrentUser,  # noqa: ARG001
) -> SourcesResponse:
    try:
        items = await list_indexed_sources(limit=2000)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Indeks nedostupan: {exc}",
        ) from exc

    return SourcesResponse(
        items=[IndexedSource(**item) for item in items],
        total=len(items),
    )
