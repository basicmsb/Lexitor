from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from src.knowledge_base.chunker import Chunk
from src.knowledge_base.embedder import embed_passages, embed_query
from src.utils.config import settings

logger = logging.getLogger(__name__)

DKOM_COLLECTION = "dkom_decisions"
EMBEDDING_DIM = 1024  # Cohere embed-multilingual-v3.0


_client_instance: AsyncQdrantClient | None = None


def _client() -> AsyncQdrantClient:
    global _client_instance
    if _client_instance is None:
        _client_instance = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
        )
    return _client_instance


@dataclass
class SearchHit:
    klasa: str
    predmet: str
    page: int | None
    chunk_index: int
    text: str
    score: float
    pdf_url: str | None
    odluka_datum: str | None
    year: str | None


async def ensure_collection(name: str = DKOM_COLLECTION) -> None:
    qdrant = _client()
    try:
        await qdrant.get_collection(name)
        return
    except (UnexpectedResponse, ValueError):
        pass
    await qdrant.create_collection(
        collection_name=name,
        vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
    )
    logger.info("Created Qdrant collection %s", name)


async def index_chunks(
    *,
    chunks: Sequence[Chunk],
    metadata: dict[str, Any],
    point_id_prefix: str,
    collection: str = DKOM_COLLECTION,
) -> int:
    if not chunks:
        return 0
    vectors = await embed_passages([c.text for c in chunks])
    points = [
        PointStruct(
            id=_deterministic_id(point_id_prefix, chunk.chunk_index),
            vector=vector,
            payload={
                **metadata,
                "chunk_index": chunk.chunk_index,
                "page": chunk.page,
                "text": chunk.text,
            },
        )
        for chunk, vector in zip(chunks, vectors, strict=True)
    ]
    await _client().upsert(collection_name=collection, points=points)
    return len(points)


async def delete_by_klasa(klasa: str, collection: str = DKOM_COLLECTION) -> None:
    await _client().delete(
        collection_name=collection,
        points_selector=Filter(
            must=[FieldCondition(key="klasa", match=MatchValue(value=klasa))]
        ),
    )


async def search(
    query: str,
    *,
    limit: int = 5,
    collection: str = DKOM_COLLECTION,
    year: str | None = None,
) -> list[SearchHit]:
    vector = await embed_query(query)
    qdrant_filter: Filter | None = None
    if year is not None:
        qdrant_filter = Filter(
            must=[FieldCondition(key="year", match=MatchValue(value=year))]
        )
    response = await _client().query_points(
        collection_name=collection,
        query=vector,
        limit=limit,
        query_filter=qdrant_filter,
        with_payload=True,
    )
    result = response.points

    hits: list[SearchHit] = []
    for point in result:
        payload = dict(point.payload or {})
        hits.append(
            SearchHit(
                klasa=payload.get("klasa", ""),
                predmet=payload.get("predmet", ""),
                page=payload.get("page"),
                chunk_index=int(payload.get("chunk_index", 0)),
                text=payload.get("text", ""),
                score=float(point.score or 0.0),
                pdf_url=payload.get("pdf_url"),
                odluka_datum=payload.get("odluka_datum"),
                year=payload.get("year"),
            )
        )
    return hits


def _deterministic_id(prefix: str, chunk_index: int) -> int:
    """Qdrant requires int or UUID ids; build a stable 64-bit hash."""
    import hashlib

    raw = f"{prefix}#{chunk_index}".encode()
    digest = hashlib.blake2b(raw, digest_size=8).digest()
    return int.from_bytes(digest, byteorder="big", signed=False)
