"""Pydantic schemas za Žalbe modul.

Korisnik unese argument (slobodni tekst), sistem vraća:
- Predikciju success rate-a (uvazen rate) na temelju sličnih DKOM predmeta
- Top N sličnih presedana s verdict tagom
- Opcionalno: rate za specifičan sastav vijeća
- Opcionalno: LLM-generirani nacrt žalbe
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ClaimTypeLiteral = Literal[
    "brand_lock", "kratki_rok", "vague_kriterij", "diskrim_uvjeti",
    "neprecizna_specifikacija", "neispravna_grupacija", "kriterij_odabira",
    "ocjena_ponude", "espd_dokazi", "jamstvo", "trosak_postupka", "ostalo",
    "auto",  # auto-detect from text
]


class ZalbeAnalyzeRequest(BaseModel):
    """Korisnikov upit za analizu šanse na žalbu."""

    argument: str = Field(
        min_length=20,
        max_length=5000,
        description="Argument žalitelja (slobodni tekst, 20-5000 znakova)",
    )
    claim_type: ClaimTypeLiteral = Field(
        default="auto",
        description="Tip povrede (ili 'auto' za semantic detection)",
    )
    vijece_members: list[str] | None = Field(
        default=None,
        description=(
            "Opcionalno: imena članova vijeća koje će suditi (3 ili više). "
            "Ako navedeno, dodaje per-vijeće rate u prediction."
        ),
    )
    limit: int = Field(default=10, ge=3, le=20, description="Koliko sličnih presedana vratiti")


class SimilarPrecedent(BaseModel):
    """Jedan sličan DKOM predmet."""

    klasa: str
    predmet: str
    datum_odluke: str | None
    narucitelj: str | None
    vrsta_postupka: str | None

    # Claim-specific
    claim_type: str
    dkom_verdict: str  # uvazen / odbijen / djelomicno_uvazen / ne_razmatra
    argument_zalitelja: str
    dkom_obrazlozenje: str
    violated_article_claimed: str | None

    # Outcome
    outcome: str | None  # outcome cijele odluke

    # Metadata
    vijece: list[str]
    pdf_url: str | None
    similarity: float  # 0-1 from Qdrant


class ZalbePrediction(BaseModel):
    """Agregirana statistika za korisnikov argument."""

    n_similar: int  # koliko sličnih našli
    success_rate: float  # uvazen / (uvazen + odbijen + djelomicno*0.5)
    detected_claim_type: str  # najsličniji tip
    type_distribution: dict[str, int]  # claim_type → count

    # Per-vijeće (ako specified)
    panel_rate: float | None = None
    panel_n_cases: int | None = None
    panel_members_found: list[str] = []  # koja imena su match-ana
    panel_members_unknown: list[str] = []


class ZalbeAnalyzeResponse(BaseModel):
    """Glavni response na /zalbe/analyze."""

    prediction: ZalbePrediction
    similar_precedents: list[SimilarPrecedent]


class ZalbeGenerateRequest(BaseModel):
    """LLM-generirani nacrt žalbe (Faza C.3)."""

    argument: str
    predmet: str  # naziv predmeta nabave
    narucitelj: str
    broj_objave_eojn: str | None = None
    klasa_odluke: str | None = None  # ako se osporava DKOM odluka, navesti klasu
    selected_precedents: list[str] = []  # klase prethodnih odluka koje korisnik želi citirati


class ZalbeGenerateResponse(BaseModel):
    """Generirani tekst žalbe."""

    nacrt_text: str
    word_count: int
    cited_precedents: list[str]
    cited_zjn_articles: list[str]
