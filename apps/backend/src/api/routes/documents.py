from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import select

from sqlalchemy.orm import selectinload

from src.api.deps import CurrentUser, DbSession
from src.api.schemas.document import (
    DocumentList,
    DocumentPublic,
    DocumentSetCreate,
    DocumentSetList,
    DocumentSetPublic,
)
from src.models import Document, DocumentSet, DocumentType, TroskovnikType
from src.services.document_service import (
    DocumentValidationError,
    save_uploaded_document,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentPublic, status_code=status.HTTP_201_CREATED)
async def upload_document(
    current_user: CurrentUser,
    session: DbSession,
    file: Annotated[UploadFile, File(...)],
    document_type: Annotated[DocumentType, Form(...)] = DocumentType.TROSKOVNIK,
    troskovnik_type: Annotated[
        TroskovnikType, Form(...)
    ] = TroskovnikType.NEPOZNATO,
    set_id: Annotated[uuid.UUID | None, Form()] = None,
) -> DocumentPublic:
    """Upload jednog fajla. `set_id` opcionalno povezuje fajl s postojećim
    DocumentSet-om (multi-file DON upload zove ovaj endpoint N puta s
    istim set_id-om)."""
    if set_id is not None:
        ds = await session.get(DocumentSet, set_id)
        if ds is None or ds.project_id != current_user.project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Set ne postoji ili nije iz tvog projekta.",
            )
    try:
        document = await save_uploaded_document(
            session=session,
            upload=file,
            user=current_user,
            document_type=document_type,
            troskovnik_type=troskovnik_type,
            set_id=set_id,
        )
    except DocumentValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return DocumentPublic.model_validate(document)


@router.post(
    "/sets", response_model=DocumentSetPublic, status_code=status.HTTP_201_CREATED,
)
async def create_document_set(
    payload: DocumentSetCreate,
    current_user: CurrentUser,
    session: DbSession,
) -> DocumentSetPublic:
    """Kreiraj prazan DocumentSet (grupa fajlova jednog DON-a). Fajlovi se
    upload-aju kroz `POST /documents` s `set_id` form param-om."""
    name = payload.name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ime seta je obavezno.",
        )
    ds = DocumentSet(
        project_id=current_user.project_id,
        name=name,
        document_type=payload.document_type,
    )
    session.add(ds)
    await session.commit()
    await session.refresh(ds, attribute_names=["documents"])
    return DocumentSetPublic.model_validate(ds)


@router.get("/sets", response_model=DocumentSetList)
async def list_document_sets(
    current_user: CurrentUser,
    session: DbSession,
) -> DocumentSetList:
    stmt = (
        select(DocumentSet)
        .where(DocumentSet.project_id == current_user.project_id)
        .options(selectinload(DocumentSet.documents))
        .order_by(DocumentSet.created_at.desc())
        .limit(200)
    )
    result = await session.execute(stmt)
    sets = result.scalars().all()
    return DocumentSetList(items=[DocumentSetPublic.model_validate(s) for s in sets])


@router.get("/sets/{set_id}", response_model=DocumentSetPublic)
async def get_document_set(
    set_id: uuid.UUID,
    current_user: CurrentUser,
    session: DbSession,
) -> DocumentSetPublic:
    stmt = (
        select(DocumentSet)
        .where(DocumentSet.id == set_id)
        .options(selectinload(DocumentSet.documents))
    )
    result = await session.execute(stmt)
    ds = result.scalar_one_or_none()
    if ds is None or ds.project_id != current_user.project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Set nije pronađen."
        )
    return DocumentSetPublic.model_validate(ds)


@router.delete("/sets/{set_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document_set(
    set_id: uuid.UUID,
    current_user: CurrentUser,
    session: DbSession,
) -> Response:
    """Obriši cijeli set + sve fajlove u njemu (cascade)."""
    ds = await session.get(DocumentSet, set_id)
    if ds is None or ds.project_id != current_user.project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Set nije pronađen."
        )
    # Documents su s cascade="all, delete-orphan" pa će ih SA obrisati.
    # Storage cleanup nije sad — ostaju na disku do garbage collection-a.
    await session.delete(ds)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{document_id}", response_model=DocumentPublic)
async def update_document_meta(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    session: DbSession,
    troskovnik_type: Annotated[TroskovnikType | None, Form()] = None,
) -> DocumentPublic:
    """Override troškovnika tip nakon uploada (npr. ako je auto-detect
    pogađao ili korisnik mijenja namjeru). Trenutno samo troskovnik_type;
    proširivo na druga meta polja kasnije."""
    document = await session.get(Document, document_id)
    if document is None or document.project_id != current_user.project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nije pronađen."
        )
    if troskovnik_type is not None:
        document.troskovnik_type = troskovnik_type
    await session.commit()
    await session.refresh(document)
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


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    session: DbSession,
) -> Response:
    document = await session.get(Document, document_id)
    if document is None or document.project_id != current_user.project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dokument nije pronađen.")

    storage_path = Path(document.storage_path) if document.storage_path else None

    await session.delete(document)
    await session.commit()

    if storage_path is not None:
        try:
            if storage_path.exists():
                storage_path.unlink()
        except OSError as exc:
            logger.warning("Failed to remove %s: %s", storage_path, exc)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
