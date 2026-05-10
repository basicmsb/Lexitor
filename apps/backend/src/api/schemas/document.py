from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.models.document import DocumentType, TroskovnikType


class DocumentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    uploaded_by_id: uuid.UUID | None
    filename: str
    content_type: str
    size_bytes: int
    document_type: DocumentType
    troskovnik_type: TroskovnikType
    set_id: uuid.UUID | None = None
    created_at: datetime


class DocumentList(BaseModel):
    items: list[DocumentPublic]


class DocumentSetPublic(BaseModel):
    """Grupa fajlova jednog DON-a / nabave. `documents` su svi pojedinačni
    fajlovi u setu; jedan set može imati 1-N dokumenata."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    document_type: DocumentType
    documents: list[DocumentPublic] = []
    created_at: datetime
    updated_at: datetime


class DocumentSetList(BaseModel):
    items: list[DocumentSetPublic]


class DocumentSetCreate(BaseModel):
    """Kreiranje praznog seta. Fajlovi se dodaju kroz upload endpoint
    s `set_id` parametrom."""

    name: str
    document_type: DocumentType = DocumentType.DON
