from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any

import cohere

from src.utils.config import settings

_BATCH_SIZE = 64  # Cohere allows 96, leave headroom


def _client() -> cohere.AsyncClientV2:
    if not settings.cohere_api_key:
        raise RuntimeError("COHERE_API_KEY nije postavljen u .env.")
    return cohere.AsyncClientV2(api_key=settings.cohere_api_key)


async def _embed(
    texts: Sequence[str],
    *,
    input_type: str,
) -> list[list[float]]:
    if not texts:
        return []
    async with _client() as client:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), _BATCH_SIZE):
            batch = list(texts[start : start + _BATCH_SIZE])
            response = await client.embed(
                texts=batch,
                model=settings.cohere_embed_model,
                input_type=input_type,
                embedding_types=["float"],
            )
            embeddings: Any = response.embeddings
            # New SDK returns object with `.float` list-of-list; fallback to `[float_]`.
            if hasattr(embeddings, "float_"):
                vectors.extend(embeddings.float_)
            elif hasattr(embeddings, "float"):
                vectors.extend(embeddings.float)
            else:
                vectors.extend(embeddings)
        return vectors


async def embed_passages(texts: Sequence[str]) -> list[list[float]]:
    return await _embed(texts, input_type="search_document")


async def embed_query(text: str) -> list[float]:
    vectors = await _embed([text], input_type="search_query")
    return vectors[0]


def embed_passages_sync(texts: Sequence[str]) -> list[list[float]]:
    return asyncio.run(embed_passages(texts))


def embed_query_sync(text: str) -> list[float]:
    return asyncio.run(embed_query(text))
