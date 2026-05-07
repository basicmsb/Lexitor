from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select

from src.api.deps import CurrentUser, DbSession
from src.api.schemas.document import DocumentList, DocumentPublic
from src.models import Document, DocumentType
from src.services.document_service import (
    DocumentValidationError,
    save_uploaded_document,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentPublic, status_code=status.HTTP_201_CREATED)
async def upload_document(
    current_user: CurrentUser,
    session: DbSession,
    file: Annotated[UploadFile, File(...)],
    document_type: Annotated[DocumentType, Form(...)] = DocumentType.TROSKOVNIK,
) -> DocumentPublic:
    try:
        document = await save_uploaded_document(
            session=session,
            upload=file,
            user=current_user,
            document_type=document_type,
        )
    except DocumentValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return DocumentPublic.model_validate(document)


@router.get("", response_model=DocumentList)
async def list_documents(
    current_user: CurrentUser,
    session: DbSession,
) -> DocumentList:
    stmt = (
        select(Document)
        .where(Document.project_id == current_user.project_id)
        .order_by(Document.created_at.desc())
        .limit(100)
    )
    result = await session.execute(stmt)
    documents = result.scalars().all()
    return DocumentList(items=[DocumentPublic.model_validate(d) for d in documents])


@router.get("/{document_id}", response_model=DocumentPublic)
async def get_document(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    session: DbSession,
) -> DocumentPublic:
    document = await session.get(Document, document_id)
    if document is None or document.project_id != current_user.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nije pronađen.")
    return DocumentPublic.model_validate(document)
