"""DKOM spot-check tool — admin-only ruta za manualnu validaciju
LLM kategorizacije claim-type-ova.

Storage: JSONL u `data/02-dkom-odluke/analysis/spotcheck_feedback.jsonl`
(append-only, jedan red po feedback-u).
"""
from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.deps import CurrentUser, require_super_admin
from src.api.schemas.spotcheck import (
    ClaimSample,
    FeedbackSubmit,
    SpotcheckBatch,
    SpotcheckStats,
)

router = APIRouter(
    prefix="/admin/dkom-spotcheck",
    tags=["admin-spotcheck"],
    dependencies=[Depends(require_super_admin)],
)


# Path-evi — relativno na backend root
EXTRACTED_DIR = Path("data/02-dkom-odluke/extracted")
FEEDBACK_PATH = Path("data/02-dkom-odluke/analysis/spotcheck_feedback.jsonl")
# Scraper sidecar fajlovi (s pdf_url-om) leže pored PDF-ova po godinama
DKOM_PDF_DIRS = [
    Path("data/02-dkom-odluke/2024"),
    Path("data/02-dkom-odluke/2025"),
    Path("data/02-dkom-odluke/2026"),
]


def _build_pdf_url_lookup() -> dict[str, str]:
    """Skupi mapping {slug → pdf_url} iz scraper sidecar JSON-a (jedanput pri load-u)."""
    lookup: dict[str, str] = {}
    for pdf_dir in DKOM_PDF_DIRS:
        if not pdf_dir.exists():
            continue
        for jp in pdf_dir.glob("*.json"):
            try:
                data = json.loads(jp.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                continue
            url = data.get("pdf_url")
            if url:
                lookup[jp.stem] = url
    return lookup


def _load_all_claims() -> list[dict[str, Any]]:
    """Skupi sve claims-ove iz extracted/*.json u flat listu."""
    flat: list[dict[str, Any]] = []
    if not EXTRACTED_DIR.exists():
        return flat
    pdf_urls = _build_pdf_url_lookup()
    for jp in sorted(EXTRACTED_DIR.glob("*.json")):
        if jp.name == "all.jsonl":
            continue
        try:
            data = json.loads(jp.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        klasa = data.get("klasa", "?")
        predmet = data.get("predmet", "")
        for idx, c in enumerate(data.get("claims", [])):
            flat.append({
                "id": f"{jp.stem}#{idx}",
                "klasa": klasa,
                "predmet": predmet,
                "pdf_filename": f"{jp.stem}.pdf",
                "pdf_url": pdf_urls.get(jp.stem),
                "llm_category": c.get("type", "ostalo"),
                "dkom_verdict": c.get("dkom_verdict", "?"),
                "argument_zalitelja": c.get("argument_zalitelja", ""),
                "obrana_narucitelja": c.get("obrana_narucitelja"),
                "dkom_obrazlozenje": c.get("dkom_obrazlozenje", ""),
                "violated_article_claimed": c.get("violated_article_claimed"),
            })
    return flat


def _load_feedback() -> list[dict[str, Any]]:
    """Učitaj sve postojeće feedback redove."""
    if not FEEDBACK_PATH.exists():
        return []
    rows: list[dict[str, Any]] = []
    with FEEDBACK_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:  # noqa: BLE001
                continue
    return rows


@router.get("/batch", response_model=SpotcheckBatch)
async def get_batch(
    _user: CurrentUser,
    size: int = 50,
    seed: int = 42,
    skip_reviewed: bool = True,
) -> SpotcheckBatch:
    """Vrati random batch claims-ova za spot-check.

    - `size`: koliko claims-ova vratiti (default 50)
    - `seed`: za reproducibilan random sample (default 42)
    - `skip_reviewed`: preskoči claim-ove koji su već pregledani
    """
    all_claims = _load_all_claims()
    if not all_claims:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nema ekstrahiranih DKOM odluka. Pokreni `extract_dkom.py` prvo.",
        )

    feedback = _load_feedback()
    already_ids = {f["claim_id"] for f in feedback}

    pool = all_claims
    if skip_reviewed and already_ids:
        pool = [c for c in all_claims if c["id"] not in already_ids]

    rng = random.Random(seed + len(already_ids))  # različit sample ako ima feedback-a
    sample = rng.sample(pool, min(size, len(pool)))

    return SpotcheckBatch(
        total_claims=len(all_claims),
        sample_size=len(sample),
        seed=seed,
        items=[ClaimSample(**c) for c in sample],
        already_reviewed_ids=sorted(already_ids),
    )


@router.post("/feedback", status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    payload: FeedbackSubmit,
    user: CurrentUser,
) -> dict[str, Any]:
    """Spremi feedback za jedan claim. Append-only u JSONL."""
    FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "claim_id": payload.claim_id,
        "verdict": payload.verdict,
        "correct_category": payload.correct_category,
        "reviewed_by": user.email,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }
    with FEEDBACK_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {"ok": True}


@router.get("/stats", response_model=SpotcheckStats)
async def get_stats(_user: CurrentUser) -> SpotcheckStats:
    """Agregat statistika spot-check-a."""
    feedback = _load_feedback()
    by_verdict: Counter[str] = Counter(f["verdict"] for f in feedback)

    # Build llm-category lookup
    all_claims = _load_all_claims()
    claim_by_id = {c["id"]: c for c in all_claims}

    # Per-category accuracy
    cat_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {"correct": 0, "wrong": 0}
    )
    miscls: Counter[tuple[str, str]] = Counter()
    for fb in feedback:
        cid = fb["claim_id"]
        c = claim_by_id.get(cid)
        if not c:
            continue
        cat = c["llm_category"]
        if fb["verdict"] == "correct":
            cat_stats[cat]["correct"] += 1
        elif fb["verdict"] == "wrong":
            cat_stats[cat]["wrong"] += 1
            if fb.get("correct_category"):
                miscls[(cat, fb["correct_category"])] += 1

    correct = by_verdict.get("correct", 0)
    wrong = by_verdict.get("wrong", 0)
    decided = correct + wrong
    accuracy = correct / decided if decided else None

    return SpotcheckStats(
        total_feedback=len(feedback),
        by_verdict=dict(by_verdict),
        accuracy=accuracy,
        by_category_accuracy={
            cat: {
                "correct": s["correct"],
                "wrong": s["wrong"],
                "accuracy": s["correct"] / (s["correct"] + s["wrong"])
                if (s["correct"] + s["wrong"]) > 0
                else 0,
            }
            for cat, s in cat_stats.items()
        },
        miscls=[
            {"llm_said": k[0], "correct": k[1], "count": n}
            for k, n in miscls.most_common()
        ],
    )


@router.delete("/feedback/{claim_id}", status_code=status.HTTP_200_OK)
async def delete_feedback(
    claim_id: str,
    _user: CurrentUser,
) -> dict[str, Any]:
    """Ukloni feedback za određeni claim (npr. ako si pogriješio kategoriju).
    Re-write cijeli JSONL bez te linije."""
    feedback = _load_feedback()
    filtered = [f for f in feedback if f["claim_id"] != claim_id]
    if len(filtered) == len(feedback):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback za taj claim ne postoji.",
        )
    with FEEDBACK_PATH.open("w", encoding="utf-8") as f:
        for row in filtered:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {"ok": True, "removed": 1}
