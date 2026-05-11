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
DKOM_CLAIMS_COLLECTION = "dkom_claims"
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


@dataclass
class ClaimHit:
    """Hit iz dkom_claims collection-a — claim-level, granularniji od SearchHit."""
    klasa: str
    predmet: str
    claim_index: int
    claim_type: str
    dkom_verdict: str  # uvazen / odbijen / djelomicno_uvazen / ne_razmatra
    argument_zalitelja: str
    obrana_narucitelja: str | None
    dkom_obrazlozenje: str
    violated_article_claimed: str | None
    outcome: str | None  # outcome cijele odluke (usvojena/odbijena/...)
    narucitelj_ime: str | None
    datum_odluke: str | None
    vijece: list[str]
    pdf_url: str | None
    score: float


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


async def list_indexed_sources(
    *,
    collection: str = DKOM_COLLECTION,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    """Return one entry per indexed legal source, deduped by klasa.

    The Qdrant collection holds one point per chunk; we sweep all points
    and group by klasa so the documentation page can list each ZJN article
    or DKOM decision exactly once.
    """
    qdrant = _client()
    seen: dict[str, dict[str, Any]] = {}
    next_offset: Any = None
    while True:
        records, next_offset = await qdrant.scroll(
            collection_name=collection,
            limit=256,
            offset=next_offset,
            with_payload=True,
            with_vectors=False,
        )
        for point in records:
            payload = dict(point.payload or {})
            klasa = payload.get("klasa") or ""
            if not klasa or klasa in seen:
                continue
            seen[klasa] = {
                "source": payload.get("source", ""),
                "klasa": klasa,
                "predmet": payload.get("predmet", ""),
                "narucitelj": payload.get("narucitelj", ""),
                "vrsta": payload.get("vrsta", ""),
                "year": payload.get("year", ""),
                "odluka_datum": payload.get("odluka_datum", ""),
                "pdf_url": payload.get("pdf_url", ""),
                "article_number": payload.get("article_number"),
            }
        if next_offset is None or len(seen) >= limit:
            break

    items = list(seen.values())
    # ZJN first (sorted by article number), then DKOM by klasa
    items.sort(
        key=lambda x: (
            0 if x.get("source") == "zjn" else 1,
            x.get("article_number") if isinstance(x.get("article_number"), int) else 10**9,
            x.get("klasa", ""),
        )
    )
    return items[:limit]


async def search(
    query: str,
    *,
    limit: int = 5,
    collection: str = DKOM_COLLECTION,
    year: str | None = None,
    source: str | None = None,
) -> list[SearchHit]:
    vector = await embed_query(query)
    must: list[FieldCondition] = []
    if year is not None:
        must.append(FieldCondition(key="year", match=MatchValue(value=year)))
    if source is not None:
        must.append(FieldCondition(key="source", match=MatchValue(value=source)))
    qdrant_filter: Filter | None = Filter(must=must) if must else None
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


# ---------------------------------------------------------------------------
# Claim-level search (granularniji od whole-decision search)


_PDF_URL_LOOKUP_CACHE: dict[str, str] | None = None


def _pdf_url_for_klasa(klasa: str) -> str | None:
    """Lookup pdf_url iz scraper sidecar JSON-a (cache-irano nakon prvog poziva)."""
    global _PDF_URL_LOOKUP_CACHE
    if _PDF_URL_LOOKUP_CACHE is None:
        import json
        from pathlib import Path
        _PDF_URL_LOOKUP_CACHE = {}
        for ydir_name in ("2024", "2025", "2026"):
            ydir = Path("data/02-dkom-odluke") / ydir_name
            if not ydir.exists():
                continue
            for jp in ydir.glob("*.json"):
                try:
                    data = json.loads(jp.read_text(encoding="utf-8"))
                except Exception:  # noqa: BLE001
                    continue
                k = data.get("klasa")
                url = data.get("pdf_url")
                if k and url:
                    _PDF_URL_LOOKUP_CACHE[k] = url
    return _PDF_URL_LOOKUP_CACHE.get(klasa)


async def search_claims(
    query: str,
    *,
    limit: int = 5,
    claim_type: str | None = None,
    only_uvazen: bool = False,
) -> list[ClaimHit]:
    """Pretraga claim-level Qdrant collection-a.

    Args:
        query: tekst za semantic search (npr. text DON bloka koji je flagat)
        limit: koliko hit-ova vratiti
        claim_type: filtriraj po tipu (npr. "brand_lock") — None znači sve
        only_uvazen: ako True, vrati samo uvazene presedane (signal za detekciju);
                     ako False, vraća sve verdikte (i odbijene kao anti-pattern).
    """
    vector = await embed_query(query)
    must: list[FieldCondition] = []
    if claim_type is not None:
        must.append(FieldCondition(key="claim_type", match=MatchValue(value=claim_type)))
    if only_uvazen:
        must.append(FieldCondition(key="dkom_verdict", match=MatchValue(value="uvazen")))
    qdrant_filter: Filter | None = Filter(must=must) if must else None
    response = await _client().query_points(
        collection_name=DKOM_CLAIMS_COLLECTION,
        query=vector,
        limit=limit,
        query_filter=qdrant_filter,
        with_payload=True,
    )

    hits: list[ClaimHit] = []
    for point in response.points:
        pl = dict(point.payload or {})
        klasa = pl.get("klasa", "")
        hits.append(
            ClaimHit(
                klasa=klasa,
                predmet=pl.get("predmet", ""),
                claim_index=int(pl.get("claim_index", 0)),
                claim_type=pl.get("claim_type", "ostalo"),
                dkom_verdict=pl.get("dkom_verdict", "?"),
                argument_zalitelja=pl.get("argument_zalitelja", ""),
                obrana_narucitelja=pl.get("obrana_narucitelja"),
                dkom_obrazlozenje=pl.get("dkom_obrazlozenje", ""),
                violated_article_claimed=pl.get("violated_article_claimed"),
                outcome=pl.get("outcome"),
                narucitelj_ime=pl.get("narucitelj_ime"),
                datum_odluke=pl.get("datum_odluke"),
                vijece=pl.get("vijece", []),
                pdf_url=_pdf_url_for_klasa(klasa),
                score=float(point.score or 0.0),
            )
        )
    return hits
