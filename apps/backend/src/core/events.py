from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict
from typing import Any


class AnalysisEventBus:
    """In-process pub/sub for SSE event streaming.

    Production deploys should swap this for Redis pub/sub or a Celery result
    backend, but for the PoC we keep it in-memory and per-process.
    """

    def __init__(self) -> None:
        self._subscribers: dict[uuid.UUID, list[asyncio.Queue[dict[str, Any]]]] = defaultdict(list)

    def subscribe(self, analysis_id: uuid.UUID) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._subscribers[analysis_id].append(queue)
        return queue

    def unsubscribe(self, analysis_id: uuid.UUID, queue: asyncio.Queue[dict[str, Any]]) -> None:
        if queue in self._subscribers.get(analysis_id, []):
            self._subscribers[analysis_id].remove(queue)
        if not self._subscribers.get(analysis_id):
            self._subscribers.pop(analysis_id, None)

    async def publish(self, analysis_id: uuid.UUID, event: dict[str, Any]) -> None:
        for queue in list(self._subscribers.get(analysis_id, [])):
            await queue.put(event)


bus = AnalysisEventBus()
