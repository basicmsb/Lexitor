"""Index DKOM claims u Qdrant kao novi collection `dkom_claims`.

Razlika od postojećeg `dkom_decisions` collection-a:
- `dkom_decisions`: whole-decision chunked (multiple points per decision)
- `dkom_claims`: jedan point po claim-u (granularniji)

Cilj: omogućiti citation enrichment na claim-level umjesto whole-decision.
Kad naš DON rule (npr. brand_lock) flaga blok, želimo retrieve-ati slične
DKOM claims-ove (s argumentom žalitelja i DKOM obrazloženjem), ne cijele
odluke gdje treba dodatno parse-ati.

Usage:
    python scripts/index_dkom_claims.py            # index sve claims
    python scripts/index_dkom_claims.py --recreate # drop + recreate
    python scripts/index_dkom_claims.py --limit 50 # test sa N claims-ova
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import sys
from pathlib import Path
from typing import Any

# Windows event loop fix za psycopg
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Add backend src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qdrant_client.http.exceptions import UnexpectedResponse  # noqa: E402
from qdrant_client.http.models import (  # noqa: E402
    Distance,
    PointStruct,
    VectorParams,
)

from src.knowledge_base.embedder import embed_passages  # noqa: E402
from src.knowledge_base.indexer import _client, EMBEDDING_DIM  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("index_dkom_claims")


CLAIMS_COLLECTION = "dkom_claims"


def _claim_id(klasa: str, claim_index: int) -> int:
    """Deterministic 64-bit hash za (klasa, claim_index)."""
    raw = f"{klasa}#{claim_index}".encode()
    digest = hashlib.blake2b(raw, digest_size=8).digest()
    return int.from_bytes(digest, byteorder="big", signed=False)


def _claim_text_for_embedding(claim: dict[str, Any]) -> str:
    """Sastavi tekst koji ide u embedding: argument + obrazloženje + članak."""
    parts = []
    if claim.get("argument_zalitelja"):
        parts.append(f"Argument: {claim['argument_zalitelja']}")
    if claim.get("obrana_narucitelja"):
        parts.append(f"Obrana: {claim['obrana_narucitelja']}")
    if claim.get("dkom_obrazlozenje"):
        parts.append(f"DKOM: {claim['dkom_obrazlozenje']}")
    if claim.get("violated_article_claimed"):
        parts.append(f"Članak: {claim['violated_article_claimed']}")
    return "\n\n".join(parts)


def load_all_claims(extracted_dir: Path) -> list[dict[str, Any]]:
    """Flat lista svih claim-ova s metadatima odluke."""
    claims = []
    for jp in sorted(extracted_dir.glob("*.json")):
        if jp.name == "all.jsonl":
            continue
        try:
            data = json.loads(jp.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        klasa = data.get("klasa", "?")
        for idx, c in enumerate(data.get("claims", [])):
            text = _claim_text_for_embedding(c)
            if len(text) < 50:  # premali da bi bio koristan
                continue
            claims.append({
                "id": _claim_id(klasa, idx),
                "text": text,
                "payload": {
                    "klasa": klasa,
                    "predmet": data.get("predmet", ""),
                    "claim_index": idx,
                    "claim_type": c.get("type", "ostalo"),
                    "dkom_verdict": c.get("dkom_verdict", "?"),
                    "argument_zalitelja": c.get("argument_zalitelja", ""),
                    "obrana_narucitelja": c.get("obrana_narucitelja"),
                    "dkom_obrazlozenje": c.get("dkom_obrazlozenje", ""),
                    "violated_article_claimed": c.get("violated_article_claimed"),
                    "outcome": data.get("outcome"),
                    "vrsta_postupka": data.get("vrsta_postupka"),
                    "narucitelj_ime": data.get("narucitelj_ime"),
                    "datum_odluke": data.get("datum_odluke"),
                    "vijece": [m["ime"] for m in data.get("vijece", [])],
                    "broj_objave_eojn": data.get("broj_objave_eojn"),
                },
            })
    return claims


async def ensure_claims_collection(*, recreate: bool = False) -> None:
    qdrant = _client()
    if recreate:
        try:
            await qdrant.delete_collection(CLAIMS_COLLECTION)
            log.info("Deleted existing collection %s", CLAIMS_COLLECTION)
        except (UnexpectedResponse, ValueError):
            pass
    try:
        await qdrant.get_collection(CLAIMS_COLLECTION)
        log.info("Collection %s već postoji", CLAIMS_COLLECTION)
        return
    except (UnexpectedResponse, ValueError):
        pass
    await qdrant.create_collection(
        collection_name=CLAIMS_COLLECTION,
        vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
    )
    log.info("Created collection %s (%d dim, cosine)", CLAIMS_COLLECTION, EMBEDDING_DIM)


async def index_claims_batch(claims: list[dict[str, Any]]) -> int:
    """Embed + upsert batch claim-ova u Qdrant."""
    if not claims:
        return 0
    texts = [c["text"] for c in claims]
    vectors = await embed_passages(texts)
    points = [
        PointStruct(id=c["id"], vector=v, payload=c["payload"])
        for c, v in zip(claims, vectors, strict=True)
    ]
    await _client().upsert(collection_name=CLAIMS_COLLECTION, points=points)
    return len(points)


async def main_async(args) -> int:
    extracted_dir = Path(args.input)
    if not extracted_dir.exists():
        log.error("Direktorij %s ne postoji", extracted_dir)
        return 1

    await ensure_claims_collection(recreate=args.recreate)

    log.info("Učitavam claim-ove iz %s ...", extracted_dir)
    claims = load_all_claims(extracted_dir)
    log.info("Pronađeno %d claim-ova", len(claims))

    if args.limit:
        claims = claims[: args.limit]
        log.info("Limit aktiviran — radim s %d claim-ova", len(claims))

    # Batchamo po 100 (Cohere limit za passage embedding requests)
    batch_size = 96
    total = 0
    for i in range(0, len(claims), batch_size):
        batch = claims[i : i + batch_size]
        n = await index_claims_batch(batch)
        total += n
        log.info("  [%d / %d] indeksirano", total, len(claims))

    log.info("=" * 60)
    log.info("Ukupno indeksirano: %d claim-ova u collection '%s'", total, CLAIMS_COLLECTION)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", type=Path,
        default=Path("data/02-dkom-odluke/extracted"),
    )
    parser.add_argument(
        "--recreate", action="store_true",
        help="Drop postojeći collection i recreate",
    )
    parser.add_argument("--limit", type=int, default=None, help="Test sa N claims-ova")
    args = parser.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
