"""Walka kroz data/01-zakoni/*/ subdirektorije i indeksira articles.jsonl
od svakog u Qdrant. Generaalizacija index_zjn.py-a — radi za sve zakone
i pravilnike skidane preko scrape_legislation.py.

Usage:
    poetry run python scripts/index_legislation.py
    poetry run python scripts/index_legislation.py --root data/01-zakoni
    poetry run python scripts/index_legislation.py --skip-existing zjn

Klasa format: "{NN broj} čl. {N}" (npr. "NN 65/2017 čl. 12") za
non-ZJN zakone. Za ZJN zadržan je "ZJN čl. N" format (kompatibilno sa
postojećim retrieve-om u analyzer-u).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

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
    p = argparse.ArgumentParser(description="Index sve zakone iz data/01-zakoni/")
    p.add_argument(
        "--root", type=Path, default=Path("data/01-zakoni"),
        help="Root direktorij s subdirektorijima (default: data/01-zakoni)",
    )
    p.add_argument(
        "--skip", nargs="*", default=["zjn"],
        help="Subdirektoriji za preskočiti (default: zjn — već indeksiran)",
    )
    p.add_argument("--verbose", "-v", action="store_true")
    return p.parse_args()


def discover(root: Path, skip: set[str]) -> list[Path]:
    """Pronađi sve poddirektorije s articles.jsonl koji NISU u skip listi."""
    if not root.exists():
        return []
    found = []
    for sub in sorted(root.iterdir()):
        if not sub.is_dir() or sub.name in skip:
            continue
        if (sub / "articles.jsonl").exists():
            found.append(sub)
    return found


def _classify_subdir(subdir: str, ref: str) -> str:
    """Vrati prefiks klasa-e na temelju imena subdirectoria + reference.

    Pravila:
      zjn-* → 'ZJN'  (kompatibilno s postojećim ZJN izlazima)
      pravilnik-* → 'Pravilnik {NN}'
      zakon-* → 'Zakon {NN}'
      ostalo → '{NN}'
    """
    nn = ref or ""  # "NN 65/2017"
    name_lower = subdir.lower()
    if name_lower.startswith("zjn"):
        return f"ZJN ({nn})"
    if name_lower.startswith("pravilnik"):
        return f"Pravilnik {nn}".strip()
    if name_lower.startswith("zakon"):
        return f"Zakon {nn}".strip()
    return nn or subdir


async def index_subdir(subdir: Path, *, verbose: bool = False) -> tuple[int, int, int]:
    """Indeksiraj jedan subdirektorij. Vraća (chunks_indexed, skipped, failed)."""
    articles_path = subdir / "articles.jsonl"
    metadata_path = subdir / "metadata.json"
    metadata: dict[str, Any] = {}
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    articles: list[dict[str, Any]] = []
    with articles_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                articles.append(json.loads(line))

    name = metadata.get("title") or subdir.name
    ref = metadata.get("reference") or ""
    pdf_url = metadata.get("url") or ""
    classifier = _classify_subdir(subdir.name, ref)
    year = ref.rsplit("/", 1)[-1] if "/" in ref else ""

    print(f"  Indexiranje {subdir.name}: {len(articles)} članaka", flush=True)

    total = 0
    skipped = 0
    failed = 0
    for idx, art in enumerate(articles, 1):
        number = art.get("number") or idx
        text = (art.get("text") or "").strip()
        if not text:
            skipped += 1
            continue
        chunks = chunk_text(text)
        if not chunks:
            skipped += 1
            continue
        klasa = f"{classifier} čl. {number}"
        payload = {
            "source": "zakon",  # legislation umbrella; analyzer rješava po klasa prefiksu
            "klasa": klasa,
            "predmet": art.get("title") or art.get("header") or f"Članak {number}.",
            "narucitelj": "",
            "zalitelj": "",
            "vrsta": art.get("dio") or "",
            "year": year,
            "odluka_datum": "",
            "pdf_url": pdf_url,
            "article_number": number,
            "dio": art.get("dio") or "",
            "glava": art.get("glava") or "",
            "subdir": subdir.name,
            "title": name,
        }
        try:
            count = await index_chunks(
                chunks=chunks,
                metadata=payload,
                point_id_prefix=f"{subdir.name}-{number}",
            )
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"    FAIL čl. {number}: {exc}", flush=True)
            continue
        total += count
        if verbose:
            print(f"    OK čl. {number}: {count} chunk(s)")
    return total, skipped, failed


async def run(args: argparse.Namespace) -> int:
    skip = set(args.skip or [])
    subdirs = discover(args.root, skip)
    if not subdirs:
        print(f"Nije pronađen niti jedan subdirektorij u {args.root}", file=sys.stderr)
        return 1
    print(f"Pronašao {len(subdirs)} zakonskih izvora za indexirati.")
    await ensure_collection()
    total_chunks = 0
    total_skipped = 0
    total_failed = 0
    for sub in subdirs:
        chunks, skipped, failed = await index_subdir(sub, verbose=args.verbose)
        total_chunks += chunks
        total_skipped += skipped
        total_failed += failed
    print(
        f"\nDone. subdirectories={len(subdirs)} chunks={total_chunks} "
        f"skipped={total_skipped} failed={total_failed}"
    )
    return 0 if total_failed == 0 else 1


def main() -> int:
    return asyncio.run(run(parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
