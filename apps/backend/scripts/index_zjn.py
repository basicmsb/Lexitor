"""Index ZJN articles (produced by scrape_zjn.py) into the same Qdrant
collection as the DKOM decisions, distinguished by `source` payload.

Usage (from apps/backend/):
    poetry run python scripts/index_zjn.py
    poetry run python scripts/index_zjn.py --root data/01-zakoni/zjn
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.knowledge_base import (  # noqa: E402
    chunk_text,
    ensure_collection,
    index_chunks,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Indeksiranje ZJN članaka u Qdrant")
    p.add_argument(
        "--root",
        type=Path,
        default=Path("data/01-zakoni/zjn"),
        help="Direktorij s articles.jsonl iz scrape_zjn.py",
    )
    p.add_argument("--max", type=int, default=None, help="Maksimalan broj članaka")
    p.add_argument("--verbose", "-v", action="store_true")
    return p.parse_args()


async def run(args: argparse.Namespace) -> int:
    articles_path = args.root / "articles.jsonl"
    metadata_path = args.root / "metadata.json"
    if not articles_path.exists():
        print(f"Nije pronađen {articles_path} — pokreni scrape_zjn.py prvo.", file=sys.stderr)
        return 1

    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
    articles: list[dict[str, object]] = []
    with articles_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                articles.append(json.loads(line))

    if args.max is not None:
        articles = articles[: args.max]

    print(f"Pronašao {len(articles)} članaka.", file=sys.stderr)
    await ensure_collection()

    indexed_total = 0
    skipped = 0
    failed = 0

    for idx, art in enumerate(articles, start=1):
        number = art.get("number", idx)
        text = (art.get("text") or "").strip()
        if not text:
            skipped += 1
            continue

        chunks = chunk_text(text)
        if not chunks:
            skipped += 1
            continue

        payload = {
            "source": "zjn",
            "klasa": f"ZJN čl. {number}",
            "predmet": art.get("title") or art.get("header") or f"Članak {number}.",
            "narucitelj": "",
            "zalitelj": "",
            "vrsta": art.get("dio") or "",
            "year": str(metadata.get("reference", "")).split("/")[-1] or "2016",
            "odluka_datum": "",
            "pdf_url": metadata.get("url", ""),
            "article_number": number,
            "dio": art.get("dio") or "",
            "glava": art.get("glava") or "",
        }

        try:
            count = await index_chunks(
                chunks=chunks,
                metadata=payload,
                point_id_prefix=f"zjn-{number}",
            )
        except Exception as exc:
            failed += 1
            print(f"  [{idx}/{len(articles)}] FAIL Članak {number}: {exc}", file=sys.stderr)
            continue

        indexed_total += count
        if args.verbose:
            print(f"  [{idx}/{len(articles)}] OK   Članak {number}: {count} chunk(s)")

    print(
        f"\nDone. articles={len(articles)} chunks={indexed_total} "
        f"skipped={skipped} failed={failed}",
        file=sys.stderr,
    )
    return 0 if failed == 0 else 1


def main() -> int:
    args = parse_args()
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
