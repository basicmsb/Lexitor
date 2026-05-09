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
    created_at: datetime


class DocumentList(BaseModel):
    items: list[DocumentPublic]
