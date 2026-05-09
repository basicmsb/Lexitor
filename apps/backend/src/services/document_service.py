from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.document_parser import supported_extensions
from src.models import Document, DocumentType, TroskovnikType, User
from src.utils.config import settings

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB


class DocumentValidationError(Exception):
    """Raised when an uploaded file fails validation."""


def _resolve_extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in supported_extensions():
        raise DocumentValidationError(
            f"Format „{suffix}” nije podržan. Dozvoljeni: {', '.join(sorted(supported_extensions()))}."
        )
    return suffix


def _resolve_storage_dir(project_id: uuid.UUID) -> Path:
    base = Path(settings.local_storage_path).resolve()
    target = base / str(project_id)
    target.mkdir(parents=True, exist_ok=True)
    return target


async def save_uploaded_document(
    *,
    session: AsyncSession,
    upload: UploadFile,
    user: User,
    document_type: DocumentType,
    troskovnik_type: TroskovnikType | None = None,
) -> Document:
    if not upload.filename:
        raise DocumentValidationError("Nedostaje ime datoteke.")

    suffix = _resolve_extension(upload.filename)
    payload = await upload.read()
    if len(payload) == 0:
        raise DocumentValidationError("Datoteka je prazna.")
    if len(payload) > MAX_UPLOAD_BYTES:
        raise DocumentValidationError(
            f"Datoteka prelazi maksimum od {MAX_UPLOAD_BYTES // (1024 * 1024)} MB."
        )

    document_id = uuid.uuid4()
    target_dir = _resolve_storage_dir(user.project_id)
    storage_path = target_dir / f"{document_id}{suffix}"
    storage_path.write_bytes(payload)

    document = Document(
        id=document_id,
        project_id=user.project_id,
        uploaded_by_id=user.id,
        filename=upload.filename,
        content_type=upload.content_type or "application/octet-stream",
        size_bytes=len(payload),
        storage_path=str(storage_path),
        document_type=document_type,
        troskovnik_type=troskovnik_type or TroskovnikType.NEPOZNATO,
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)
    return document
