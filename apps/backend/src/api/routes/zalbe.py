"""Žalbe modul — search + predikcija + (kasnije) generiranje nacrta.

C.1 (gotovo): /zalbe/analyze — korisnik unese argument, vraća se predikcija
success rate-a + slični DKOM presedani.

C.2 (uskoro): per-vijeće rate u prediction.

C.3 (uskoro): /zalbe/generate — LLM nacrt žalbe.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.deps import CurrentUser
from src.api.schemas.zalbe import (
    SimilarPrecedent,
    ZalbeAnalyzeRequest,
    ZalbeAnalyzeResponse,
    ZalbePrediction,
)

router = APIRouter(prefix="/zalbe", tags=["zalbe"])


# Path do extracted DKOM dataset-a za per-vijeće lookup (in-memory cache pri prvom pozivu)
EXTRACTED_DIR = Path("data/02-dkom-odluke/extracted")
_VIJECE_INDEX_CACHE: dict[str, list[dict[str, Any]]] | None = None


def _build_vijece_index() -> dict[str, list[dict[str, Any]]]:
    """Index member_name → lista [{klasa, claim_type, verdict}]."""
    global _VIJECE_INDEX_CACHE
    if _VIJECE_INDEX_CACHE is not None:
        return _VIJECE_INDEX_CACHE

    index: dict[str, list[dict[str, Any]]] = {}
    for jp in EXTRACTED_DIR.glob("*.json"):
        if jp.name == "all.jsonl":
            continue
        try:
            data = json.loads(jp.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        klasa = data.get("klasa", "?")
        members = [m["ime"] for m in data.get("vijece", [])]
        for claim in data.get("claims", []):
            entry = {
                "klasa": klasa,
                "claim_type": claim.get("type", "ostalo"),
                "verdict": claim.get("dkom_verdict", "?"),
                "members": members,
            }
            for m in members:
                index.setdefault(m, []).append(entry)
    _VIJECE_INDEX_CACHE = index
    return index


def _normalize_member_name(name: str) -> str:
    """Pojednostavi normalizaciju za fuzzy match (lowercase, no diacritics)."""
    table = str.maketrans({
        "č": "c", "ć": "c", "ž": "z", "š": "s", "đ": "d",
        "Č": "c", "Ć": "c", "Ž": "z", "Š": "s", "Đ": "d",
    })
    return re.sub(r"\s+", " ", name.translate(table).lower().strip())


def _calculate_success_rate(verdicts: list[str]) -> float | None:
    """Izračunaj uvazen rate. None ako nema decided slučajeva."""
    uvazen = sum(1 for v in verdicts if v == "uvazen")
    djelomicno = sum(1 for v in verdicts if v == "djelomicno_uvazen")
    odbijen = sum(1 for v in verdicts if v == "odbijen")
    decided = uvazen + djelomicno + odbijen
    if decided == 0:
        return None
    return (uvazen + 0.5 * djelomicno) / decided


@router.post("/analyze", response_model=ZalbeAnalyzeResponse)
async def analyze_zalba(
    payload: ZalbeAnalyzeRequest,
    _user: CurrentUser,
) -> ZalbeAnalyzeResponse:
    """Analiza korisnikovog argumenta:
    - Semantic search nad dkom_claims (Qdrant)
    - Agregat success rate iz top N sličnih
    - Opcionalno per-vijeće rate
    """
    from src.knowledge_base import search_claims

    # 1. Semantic search nad dkom_claims
    claim_type_filter = (
        None if payload.claim_type == "auto" else payload.claim_type
    )
    try:
        hits = await search_claims(
            payload.argument,
            limit=payload.limit,
            claim_type=claim_type_filter,
            only_uvazen=False,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Pretraga prakse nije uspjela: {exc}",
        ) from exc

    if not hits:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nije pronađen niti jedan sličan DKOM predmet. Pokušaj s drugim argumentom.",
        )

    # 2. Detect dominant claim_type (ako "auto")
    type_counts: Counter[str] = Counter(h.claim_type for h in hits)
    detected_type = (
        payload.claim_type
        if payload.claim_type != "auto"
        else type_counts.most_common(1)[0][0]
    )

    # 3. Success rate iz svih hit verdikata
    verdicts = [h.dkom_verdict for h in hits]
    success_rate = _calculate_success_rate(verdicts) or 0.0

    # 4. Per-vijeće analiza (opcionalno)
    panel_rate: float | None = None
    panel_n: int | None = None
    panel_found: list[str] = []
    panel_unknown: list[str] = []
    if payload.vijece_members:
        index = _build_vijece_index()
        # Normalize index keys za fuzzy match
        norm_to_orig = {_normalize_member_name(k): k for k in index.keys()}

        all_member_entries: list[dict[str, Any]] = []
        for name in payload.vijece_members:
            norm = _normalize_member_name(name)
            if norm in norm_to_orig:
                orig = norm_to_orig[norm]
                panel_found.append(orig)
                # Filter entries po sličnom claim_type
                entries = [
                    e for e in index[orig]
                    if e["claim_type"] == detected_type
                    and e["verdict"] in ("uvazen", "odbijen", "djelomicno_uvazen")
                ]
                all_member_entries.extend(entries)
            else:
                panel_unknown.append(name)

        # Agregat: claim-ovi gdje su BAR 2 člana iz panela bili u vijeću
        # (najslabija forma podataka; striktni "svi 3" je strožiji)
        member_set = set(panel_found)
        if member_set:
            klasa_to_count: Counter[str] = Counter()
            klasa_to_verdict: dict[str, str] = {}
            for entry in all_member_entries:
                klasa_to_count[entry["klasa"]] += 1
                klasa_to_verdict[entry["klasa"]] = entry["verdict"]
            # Uzmi klase gdje su barem 2 od n članova bili tamo
            min_overlap = max(1, len(member_set) // 2)
            panel_verdicts = [
                klasa_to_verdict[k]
                for k, n in klasa_to_count.items()
                if n >= min_overlap
            ]
            if panel_verdicts:
                panel_rate = _calculate_success_rate(panel_verdicts)
                panel_n = len(panel_verdicts)

    # 5. Build response
    prediction = ZalbePrediction(
        n_similar=len(hits),
        success_rate=success_rate,
        detected_claim_type=detected_type,
        type_distribution=dict(type_counts),
        panel_rate=panel_rate,
        panel_n_cases=panel_n,
        panel_members_found=panel_found,
        panel_members_unknown=panel_unknown,
    )
    similar = [
        SimilarPrecedent(
            klasa=h.klasa,
            predmet=h.predmet,
            datum_odluke=h.datum_odluke,
            narucitelj=h.narucitelj_ime,
            vrsta_postupka=h.outcome,  # actually outcome — we'll use it
            claim_type=h.claim_type,
            dkom_verdict=h.dkom_verdict,
            argument_zalitelja=h.argument_zalitelja,
            dkom_obrazlozenje=h.dkom_obrazlozenje,
            violated_article_claimed=h.violated_article_claimed,
            outcome=h.outcome,
            vijece=h.vijece,
            pdf_url=h.pdf_url,
            similarity=h.score,
        )
        for h in hits
    ]
    return ZalbeAnalyzeResponse(prediction=prediction, similar_precedents=similar)
