"""Project (tenant/organization) endpoints.

Currently exposes a single endpoint — uploading the company logo that
appears on PDF reports next to the Lexitor wordmark. Logo is stored
under `<local_storage_path>/projects/<project_id>/logo.<ext>` and the
path is recorded on `Project.logo_path`.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from src.api.deps import CurrentUser, DbSession
from src.models import Project
from src.utils.config import settings

router = APIRouter(prefix="/projects", tags=["projects"])
logger = logging.getLogger(__name__)


class ProjectPublic(BaseModel):
    id: str
    name: str
    slug: str
    logo_path: str | None = None
    has_logo: bool = False


_ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
_MAX_BYTES = 2 * 1024 * 1024  # 2 MB


@router.get("/me", response_model=ProjectPublic)
async def get_my_project(
    current_user: CurrentUser,
    session: DbSession,
) -> ProjectPublic:
    project = await session.get(Project, current_user.project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Projekt nije pronađen."
        )
    has_logo = bool(project.logo_path) and Path(project.logo_path).exists()
    return ProjectPublic(
        id=str(project.id),
        name=project.name,
        slug=project.slug,
        logo_path=project.logo_path if has_logo else None,
        has_logo=has_logo,
    )


@router.post("/me/logo", response_model=ProjectPublic)
async def upload_my_project_logo(
    current_user: CurrentUser,
    session: DbSession,
    file: UploadFile = File(...),
) -> ProjectPublic:
    """Upload (or replace) the project's logo. PNG/JPG/GIF/WEBP, ≤ 2 MB."""
    project = await session.get(Project, current_user.project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Projekt nije pronađen."
        )

    ext = Path(file.filename or "").suffix.lower()
    if ext not in _ALLOWED_EXT:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Logo mora biti PNG, JPG, GIF ili WEBP.",
        )

    # Read into memory to enforce size limit
    blob = await file.read()
    if len(blob) > _MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Logo je veći od 2 MB.",
        )

    base = Path(settings.local_storage_path).resolve() / "projects" / str(project.id)
    base.mkdir(parents=True, exist_ok=True)
    # Remove any older logo with a different extension
    for old in base.glob("logo.*"):
        try:
            old.unlink()
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to remove old logo %s: %s", old, e)
    target = base / f"logo{ext}"
    target.write_bytes(blob)

    project.logo_path = str(target)
    await session.commit()
    await session.refresh(project)
    return ProjectPublic(
        id=str(project.id),
        name=project.name,
        slug=project.slug,
        logo_path=project.logo_path,
        has_logo=True,
    )


@router.delete("/me/logo", response_model=ProjectPublic)
async def delete_my_project_logo(
    current_user: CurrentUser,
    session: DbSession,
) -> ProjectPublic:
    project = await session.get(Project, current_user.project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Projekt nije pronađen."
        )
    if project.logo_path:
        try:
            p = Path(project.logo_path)
            if p.exists():
                p.unlink()
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to delete logo %s: %s", project.logo_path, e)
        project.logo_path = None
        await session.commit()
        await session.refresh(project)
    return ProjectPublic(
        id=str(project.id),
        name=project.name,
        slug=project.slug,
        logo_path=None,
        has_logo=False,
    )
