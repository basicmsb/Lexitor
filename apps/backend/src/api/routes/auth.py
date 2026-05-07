from __future__ import annotations

import re
import uuid

import jwt
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from src.api.deps import CurrentUser, DbSession
from src.api.schemas.auth import (
    LoginRequest,
    MeResponse,
    ProjectPublic,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserPublic,
)
from src.models import Project, User, UserRole
from src.utils.security import (
    create_token,
    decode_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return base[:48] or "workspace"


async def _unique_slug(session: DbSession, base: str) -> str:
    candidate = base
    suffix = 0
    while True:
        stmt = select(Project).where(Project.slug == candidate)
        existing = await session.execute(stmt)
        if existing.scalar_one_or_none() is None:
            return candidate
        suffix += 1
        candidate = f"{base}-{suffix}"


def _token_pair(user: User) -> TokenPair:
    return TokenPair(
        access_token=create_token(subject=user.id, token_type="access"),
        refresh_token=create_token(subject=user.id, token_type="refresh"),
    )


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, session: DbSession) -> TokenPair:
    existing_user = await session.execute(select(User).where(User.email == payload.email))
    if existing_user.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Korisnik s tom email adresom već postoji.",
        )

    slug = await _unique_slug(session, _slugify(payload.project_name))
    project = Project(name=payload.project_name, slug=slug)
    session.add(project)
    await session.flush()

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.OWNER,
        project_id=project.id,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return _token_pair(user)


@router.post("/login", response_model=TokenPair)
async def login(payload: LoginRequest, session: DbSession) -> TokenPair:
    result = await session.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Pogrešan email ili lozinka.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Korisnički račun je deaktiviran.",
        )
    return _token_pair(user)


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, session: DbSession) -> TokenPair:
    try:
        decoded = decode_token(payload.refresh_token, expected_type="refresh")
        user_id = uuid.UUID(decoded["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token nije važeći.",
        ) from exc

    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Korisnik ne postoji.",
        )
    return _token_pair(user)


@router.get("/me", response_model=MeResponse)
async def me(current_user: CurrentUser) -> MeResponse:
    return MeResponse(
        user=UserPublic.model_validate(current_user),
        project=ProjectPublic.model_validate(current_user.project),
    )
