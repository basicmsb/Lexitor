from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from typing import Any

import cohere

from src.utils.config import settings

logger = logging.getLogger(__name__)

_BATCH_SIZE = 64  # Cohere allows 96, leave headroom
# Cohere trial key cap is 100 calls/min. Throttle to ~80 calls/min so we
# never hit the rate limit; production keys can drop the sleep.
_THROTTLE_SECONDS = 0.75
_MAX_RETRIES = 4
_RETRY_BACKOFF_BASE = 8.0  # 8s, 16s, 32s, 64s

_client_instance: cohere.AsyncClientV2 | None = None


def _client() -> cohere.AsyncClientV2:
    global _client_instance
    if not settings.cohere_api_key:
        raise RuntimeError("COHERE_API_KEY nije postavljen u .env.")
    if _client_instance is None:
        _client_instance = cohere.AsyncClientV2(api_key=settings.cohere_api_key)
    return _client_instance


async def _embed_batch_with_retry(
    client: cohere.AsyncClientV2,
    batch: list[str],
    *,
    input_type: str,
) -> list[list[float]]:
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            response = await client.embed(
                texts=batch,
                model=settings.cohere_embed_model,
                input_type=input_type,
                embedding_types=["float"],
            )
            embeddings: Any = response.embeddings
            if hasattr(embeddings, "float_"):
                return list(embeddings.float_)
            if hasattr(embeddings, "float"):
                return list(embeddings.float)
            return list(embeddings)
        except Exception as exc:  # noqa: BLE001 — Cohere wraps 429 generically
            last_exc = exc
            message = str(exc).lower()
            is_rate_limit = (
                "429" in message or "rate limit" in message or "too many" in message
            )
            if attempt == _MAX_RETRIES or not is_rate_limit:
                raise
            wait = _RETRY_BACKOFF_BASE * (2**attempt)
            logger.warning(
                "Cohere rate limit (attempt %d/%d), sleeping %.0fs",
                attempt + 1,
                _MAX_RETRIES,
                wait,
            )
            await asyncio.sleep(wait)
    if last_exc is not None:
        raise last_exc
    return []


async def _embed(
    texts: Sequence[str],
    *,
    input_type: str,
) -> list[list[float]]:
    if not texts:
        return []
    client = _client()
    vectors: list[list[float]] = []
    for start in range(0, len(texts), _BATCH_SIZE):
        if start > 0:
            await asyncio.sleep(_THROTTLE_SECONDS)
        batch = list(texts[start : start + _BATCH_SIZE])
        vectors.extend(await _embed_batch_with_retry(client, batch, input_type=input_type))
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
