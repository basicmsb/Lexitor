"""Pydantic schemas za DKOM spot-check tool (admin only)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ClaimType = Literal[
    "brand_lock", "kratki_rok", "vague_kriterij", "diskrim_uvjeti",
    "neprecizna_specifikacija", "neispravna_grupacija", "kriterij_odabira",
    "ocjena_ponude", "espd_dokazi", "jamstvo", "trosak_postupka", "ostalo",
]

Verdict = Literal["correct", "wrong", "uncertain", "skip"]


class ClaimSample(BaseModel):
    """Jedan claim za spot-check pregled."""

    id: str  # jedinstveni identifikator (klasa#claim_index)
    klasa: str
    predmet: str
    pdf_filename: str | None  # za eventualni link na PDF
    pdf_url: str | None  # public URL na DKOM PDF (https://pdf.dkom.hr/...)
    llm_category: ClaimType
    dkom_verdict: str
    argument_zalitelja: str
    obrana_narucitelja: str | None
    dkom_obrazlozenje: str
    violated_article_claimed: str | None


class SpotcheckBatch(BaseModel):
    """Batch random claims-ova za pregled."""

    total_claims: int  # ukupno claims-ova u korpusu
    sample_size: int
    seed: int
    items: list[ClaimSample]
    already_reviewed_ids: list[str]  # za skip already-done


class FeedbackSubmit(BaseModel):
    """User feedback za jedan claim."""

    claim_id: str
    verdict: Verdict
    correct_category: ClaimType | None = Field(
        default=None,
        description="Ako verdict='wrong', koja je prava kategorija",
    )


class SpotcheckStats(BaseModel):
    """Agregat statistika spot-check-a."""

    total_feedback: int
    by_verdict: dict[str, int]  # "correct": N, "wrong": N, "uncertain": N, "skip": N
    accuracy: float | None  # correct / (correct + wrong) — None ako nedovoljno feedback-a
    by_category_accuracy: dict[str, dict[str, int | float]]
    miscls: list[dict[str, str | int]]  # [{"llm_said": ..., "correct": ..., "count": N}]
