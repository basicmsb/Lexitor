from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from src.api.deps import CurrentUser
from src.api.schemas.knowledge import SearchHitPublic, SearchRequest, SearchResponse
from src.knowledge_base import search

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("/search", response_model=SearchResponse)
async def search_knowledge(
    payload: SearchRequest,
    current_user: CurrentUser,  # noqa: ARG001  — auth required
) -> SearchResponse:
    try:
        hits = await search(payload.query, limit=payload.limit, year=payload.year)
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
