from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from src.models.analysis import AnalysisItemStatus, AnalysisStatus
from src.models.citation import CitationSource


class CitationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: CitationSource
    reference: str
    snippet: str
    url: str | None


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
    citations: list[CitationPublic]


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
