"""Local dev entrypoint that sets the right asyncio policy on Windows.

psycopg async driver does not work with the default ProactorEventLoop on Windows,
so we have to switch to SelectorEventLoop *before* uvicorn imports asyncio.
Production deploys (Linux containers) will use uvicorn directly without this shim.
"""

from __future__ import annotations

import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn  # noqa: E402

if __name__ == "__main__":
    # Reload is intentionally OFF: it kills `asyncio.create_task(...)`
    # background workers (mock analyzer, etc.) every time a Python file
    # changes, which corrupts in-flight analyses. Restart the server
    # manually after backend edits during dev.
    uvicorn.run(
        "src.api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        loop="asyncio",
    )
