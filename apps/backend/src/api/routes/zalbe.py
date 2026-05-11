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

from fastapi import APIRouter, HTTPException, status

from src.api.deps import CurrentUser
from src.api.schemas.zalbe import (
    SimilarPrecedent,
    ZalbeAnalyzeRequest,
    ZalbeAnalyzeResponse,
    ZalbeGenerateRequest,
    ZalbeGenerateResponse,
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
        except Exception:  # noqa: S112
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
    except Exception as exc:
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


# ---------------------------------------------------------------------------
# C.3 — LLM nacrt žalbe

_GENERATE_SYSTEM_PROMPT = """Ti si pravni asistent specijaliziran za hrvatsko pravo javne nabave (ZJN 2016, NN 120/16, 114/22). Tvoj zadatak je napisati strukturirani nacrt žalbe DKOM-u (Državna komisija za kontrolu postupaka javne nabave) na temelju korisnikovog argumenta i sličnih DKOM presedana.

KLJUČNE UPUTE:

1. **Format nacrta** — koristi formalnu strukturu hrvatske pravne žalbe:
   - Zaglavlje: Naručitelj, žalitelj, broj objave EOJN, predmet
   - Uvod: kratki opis postupka i osnova za žalbu
   - Žalbeni navod (numerirani): konkretno što se osporava
     - U svakom navodu: što naručitelj učinio, koji ZJN članak prekršen, zašto je to problem
   - Pravni temelj: navedeni ZJN članci i DKOM presedani
   - Zahtjev: što žalitelj traži (poništenje odluke / poništenje DON-a / produljenje roka itd.)
   - Trošak postupka (ako relevantno): standard naknade

2. **Pravna terminologija** — formalna, precizna:
   - "Žalitelj", "naručitelj", "ponuditelj", "dokumentacija o nabavi (DON)"
   - "Žalbeni navod osnovan je iz sljedećih razloga: …"
   - "Sukladno članku N. stavku M. Zakona o javnoj nabavi (NN 120/16, 114/22)…"
   - "Slijedom navedenoga, žalitelj predlaže da DKOM…"

3. **Citiranje presedana** — koristi prošle DKOM odluke kao argument:
   - "DKOM je u odluci klase UP/II-034-02/25-01/N od datuma utvrdio da…"
   - Citiraj 2-3 najsličnija slučaja gdje je DKOM uvažio sličan argument
   - Ne izmišljaj klase ili datume — koristi samo one koje su priložene

4. **ZJN članci za najčešće povrede**:
   - Brand-lock: ZJN čl. 207
   - Norme bez "ili jednakovrijedno": ZJN čl. 209, 210
   - Neprecizne specifikacije: ZJN čl. 280 st. 4, čl. 290 st. 1
   - Kratki rok: ZJN čl. 219-220
   - Diskriminatorni uvjeti sposobnosti: ZJN čl. 256-272
   - Načela javne nabave: ZJN čl. 4

5. **Ton i opseg** — pisno, jasno, bez emocionalnog jezika. Nacrt cca 600-1500 riječi.

6. **NE izmišljaj** — ako neki podatak nije naveden u korisnikovom inputu (npr. evidencijski broj nabave), napiši `[…]` umjesto izmišljotine.

Vrati samo tekst nacrta žalbe, bez preambule ili objašnjenja."""


@router.post("/generate", response_model=ZalbeGenerateResponse)
async def generate_zalba(
    payload: ZalbeGenerateRequest,
    _user: CurrentUser,
) -> ZalbeGenerateResponse:
    """LLM-generirani nacrt žalbe iz korisnikovog argumenta + odabrani presedani.

    Koristi Anthropic Claude (production key, isti kao DKOM extraction).
    Korisnik može odabrati koje DKOM klase da Lexitor citira; ako ne navede,
    sustav sam pretražuje slične.
    """
    import os

    import anthropic
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LLM nije konfiguriran (ANTHROPIC_API_KEY missing).",
        )
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")

    # 1. Skupi presedane (korisnikov select ili auto-search)
    from src.knowledge_base import search_claims

    selected_data: list[dict[str, Any]] = []
    if payload.selected_precedents:
        # Korisnik već odabrao konkretne klase — učitaj ih iz dataset-a
        for jp in EXTRACTED_DIR.glob("*.json"):
            if jp.name == "all.jsonl":
                continue
            try:
                data = json.loads(jp.read_text(encoding="utf-8"))
            except Exception:  # noqa: S112
                continue
            if data.get("klasa") in payload.selected_precedents:
                selected_data.append(data)
    else:
        # Auto-search slično za korisnikov argument
        try:
            hits = await search_claims(payload.argument, limit=5)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Pretraga prakse nije uspjela: {exc}",
            ) from exc
        for h in hits:
            selected_data.append({
                "klasa": h.klasa,
                "predmet": h.predmet,
                "datum_odluke": h.datum_odluke,
                "outcome": h.outcome,
                "claims": [{
                    "type": h.claim_type,
                    "argument_zalitelja": h.argument_zalitelja,
                    "dkom_obrazlozenje": h.dkom_obrazlozenje,
                    "violated_article_claimed": h.violated_article_claimed,
                    "dkom_verdict": h.dkom_verdict,
                }],
            })

    # 2. Build prompt user content
    precedents_text = ""
    for d in selected_data[:5]:
        precedents_text += (
            f"\n--- DKOM odluka {d.get('klasa', '?')} "
            f"({d.get('datum_odluke', '?')}) ---\n"
            f"Predmet: {d.get('predmet', '')}\n"
            f"Ishod: {d.get('outcome', '?')}\n"
        )
        for c in d.get("claims", [])[:2]:
            precedents_text += (
                f"  Argument: {(c.get('argument_zalitelja') or '')[:300]}\n"
                f"  DKOM: {(c.get('dkom_obrazlozenje') or '')[:300]}\n"
                f"  Članak: {c.get('violated_article_claimed') or '?'}\n"
                f"  Verdikt: {c.get('dkom_verdict', '?')}\n"
            )

    user_content = (
        f"Napiši nacrt žalbe DKOM-u za sljedeći slučaj:\n\n"
        f"PREDMET NABAVE: {payload.predmet}\n"
        f"NARUČITELJ: {payload.narucitelj}\n"
        f"BROJ OBJAVE EOJN: {payload.broj_objave_eojn or '[broj objave]'}\n"
        f"KLASA OSPORAVANE ODLUKE: {payload.klasa_odluke or '[klasa]'}\n\n"
        f"ARGUMENT ŽALITELJA:\n{payload.argument}\n\n"
        f"SLIČNI DKOM PRESEDANI ZA REFERENCU:\n{precedents_text}"
    )

    # 3. Call Claude
    try:
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model=model,
            max_tokens=4096,
            system=[
                {
                    "type": "text",
                    "text": _GENERATE_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_content}],
        )
    except anthropic.APIError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM zahtjev nije uspio: {exc}",
        ) from exc

    nacrt = "".join(b.text for b in msg.content if hasattr(b, "text"))
    if not nacrt:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LLM nije vratio sadržaj.",
        )

    # 4. Extract cited precedents and ZJN articles iz teksta nacrta (best-effort)
    cited_precedents = list(set(
        re.findall(r"UP/II-\d{3}-\d{2}/\d{2}-\d{2}/\d+", nacrt)
    ))
    cited_zjn = list(set(
        re.findall(r"(?:čl(?:ank[au]?)?\.?\s*)(\d{1,3})", nacrt, re.IGNORECASE)
    ))

    return ZalbeGenerateResponse(
        nacrt_text=nacrt.strip(),
        word_count=len(nacrt.split()),
        cited_precedents=cited_precedents,
        cited_zjn_articles=cited_zjn,
    )
