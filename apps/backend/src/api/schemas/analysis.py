from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from src.models.analysis import AnalysisItemStatus, AnalysisStatus, UserVerdict
from src.models.citation import CitationSource


class CitationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: CitationSource
    reference: str
    snippet: str
    url: str | None


class HighlightSpan(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    start: int
    end: int
    label: str
    kind: str = "match"


class FindingCitation(BaseModel):
    source: str
    reference: str
    snippet: str | None = None
    url: str | None = None


class FindingPublic(BaseModel):
    """One Lexitor nalaz on a stavka. A stavka can have many — e.g.
    brand_lock + arithmetic_mismatch + missing_jm together. Each finding
    is independently rendered + (in future) gets its own user verdict."""

    kind: str  # "brand_lock", "arithmetic_mismatch", "missing_jm", "mock", …
    status: AnalysisItemStatus
    explanation: str | None = None
    suggestion: str | None = None
    is_mock: bool = False
    citations: list[FindingCitation] = []


class AnalysisItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    position: int
    label: str | None
    text: str
    status: AnalysisItemStatus
    explanation: str | None
    suggestion: str | None
    metadata_json: dict[str, Any] | None
    highlights: list[HighlightSpan] | None = None
    citations: list[CitationPublic]
    findings: list[FindingPublic] | None = None
    user_verdict: UserVerdict | None = None
    user_comment: str | None = None
    include_in_pdf: bool = True


class AnalysisItemFeedbackUpdate(BaseModel):
    """Request body for PATCH /analyses/{id}/items/{item_id}.

    All fields optional — client sends only what changed (autosave-style).
    Server validates that user_comment is non-empty when verdict=incorrect.
    """

    user_verdict: UserVerdict | None = None
    user_comment: str | None = None
    include_in_pdf: bool | None = None
    # Sentinel to clear verdict/comment without omitting the field
    clear_verdict: bool = False


class AnalysisPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    status: AnalysisStatus
    progress_percent: int
    error_message: str | None
    summary: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class AnalysisDetail(AnalysisPublic):
    items: list[AnalysisItemPublic]


class StartAnalysisResponse(BaseModel):
    analysis_id: uuid.UUID
    document_id: uuid.UUID
    status: AnalysisStatus
