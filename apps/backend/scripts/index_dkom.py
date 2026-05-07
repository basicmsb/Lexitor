"""Index downloaded DKOM PDFs into Qdrant for RAG.

Usage (from apps/backend/):
    poetry run python scripts/index_dkom.py
    poetry run python scripts/index_dkom.py --root data/02-dkom-odluke --max 10

Reads each {klasa}.json metadata file produced by scrape_dkom.py, parses
the matching PDF, chunks the text, embeds with Cohere, and upserts into
the `dkom_decisions` Qdrant collection.

Idempotent: re-running re-upserts the same point IDs (deterministic hash
of klasa + chunk index), so existing decisions are refreshed in place.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Ensure SelectorEventLoop on Windows so psycopg/qdrant async play nicely.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Allow `python scripts/index_dkom.py` from apps/backend root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.knowledge_base import (  # noqa: E402  (must come after sys.path tweak)
    chunk_text,
    ensure_collection,
    extract_pdf_text,
    index_chunks,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Indeksiranje DKOM odluka u Qdrant")
    p.add_argument(
        "--root",
        type=Path,
        default=Path("data/02-dkom-odluke"),
        help="Output direktorij scrape_dkom.py (default: data/02-dkom-odluke)",
    )
    p.add_argument("--max", type=int, default=None, help="Maksimalan broj odluka")
    p.add_argument("--year", type=str, default=None, help="Filtriraj po godini")
    p.add_argument("--verbose", "-v", action="store_true")
    return p.parse_args()


def discover(root: Path, *, year: str | None) -> list[Path]:
    if not root.exists():
        return []
    glob = f"{year}/*.json" if year else "*/*.json"
    return sorted(root.glob(glob))


async def run(args: argparse.Namespace) -> int:
    metadata_files = discover(args.root, year=args.year)
    if not metadata_files:
        print("Nema odluka za indeksiranje. Pokreni scrape_dkom.py prvo.", file=sys.stderr)
        return 1
    if args.max is not None:
        metadata_files = metadata_files[: args.max]

    print(f"Pronašao {len(metadata_files)} odluka.", file=sys.stderr)
    await ensure_collection()

    indexed_total = 0
    skipped = 0
    failed = 0

    for index, meta_path in enumerate(metadata_files, start=1):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"  [{index}/{len(metadata_files)}] FAIL meta {meta_path.name}: {exc}", file=sys.stderr)
            failed += 1
            continue

        pdf_path = meta_path.with_suffix(".pdf")
        if not pdf_path.exists():
            print(f"  [{index}/{len(metadata_files)}] SKIP {meta.get('klasa','?')}: PDF missing", file=sys.stderr)
            skipped += 1
            continue

        try:
            text = extract_pdf_text(pdf_path)
        except Exception as exc:
            print(f"  [{index}/{len(metadata_files)}] FAIL extract {meta.get('klasa','?')}: {exc}", file=sys.stderr)
            failed += 1
            continue

        chunks = chunk_text(text)
        if not chunks:
            print(f"  [{index}/{len(metadata_files)}] SKIP {meta.get('klasa','?')}: empty PDF", file=sys.stderr)
            skipped += 1
            continue

        payload_meta = {
            "source": "dkom",
            "klasa": meta.get("klasa", ""),
            "narucitelj": meta.get("narucitelj", ""),
            "zalitelj": meta.get("zalitelj", ""),
            "predmet": meta.get("predmet", ""),
            "vrsta": meta.get("vrsta", ""),
            "year": meta.get("year") or "",
            "odluka_datum": meta.get("odluka_datum", ""),
            "pdf_url": meta.get("pdf_url", ""),
        }

        klasa = meta.get("klasa", meta_path.stem)
        try:
            count = await index_chunks(
                chunks=chunks,
                metadata=payload_meta,
                point_id_prefix=klasa,
            )
        except Exception as exc:
            print(f"  [{index}/{len(metadata_files)}] FAIL index {klasa}: {exc}", file=sys.stderr)
            failed += 1
            continue

        indexed_total += count
        if args.verbose:
            print(f"  [{index}/{len(metadata_files)}] OK   {klasa}: {count} chunks")

    print(
        f"\nDone. odluka={len(metadata_files)} chunks={indexed_total} "
        f"skipped={skipped} failed={failed}",
        file=sys.stderr,
    )
    return 0 if failed == 0 else 1


def main() -> int:
    args = parse_args()
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
