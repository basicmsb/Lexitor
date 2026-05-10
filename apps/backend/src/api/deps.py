from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated, Callable

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_session
from src.models import (
    Module,
    Organization,
    OrganizationRole,
    OrganizationUser,
    Subscription,
    SubscriptionStatus,
    User,
)
from src.utils.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Niste prijavljeni.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(token, expected_type="access")
        user_id = uuid.UUID(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token nije važeći.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Korisnik ne postoji ili je deaktiviran.",
        )
    return user


async def get_current_organization(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    x_organization_id: Annotated[str | None, Header(alias="X-Organization-Id")] = None,
) -> Organization:
    """Aktivna organizacija — preferira `X-Organization-Id` header, fallback
    je prva organizacija u kojoj je user član.

    Throws 403 ako user nije član tražene organizacije."""
    org_id: uuid.UUID | None = None
    if x_organization_id:
        try:
            org_id = uuid.UUID(x_organization_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="X-Organization-Id nije valjan UUID.",
            ) from exc

    if org_id:
        # Provjeri je li user član
        membership = await session.scalar(
            select(OrganizationUser).where(
                OrganizationUser.user_id == user.id,
                OrganizationUser.organization_id == org_id,
            )
        )
        if not membership and not user.is_super_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Niste član ove organizacije.",
            )
        org = await session.get(Organization, org_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organizacija ne postoji.",
            )
        return org

    # No header → uzmi prvu user-ovu organizaciju
    membership = await session.scalar(
        select(OrganizationUser).where(OrganizationUser.user_id == user.id).limit(1)
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Niste član nijedne organizacije.",
        )
    org = await session.get(Organization, membership.organization_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organizacija ne postoji.",
        )
    return org


async def get_user_role_in_org(
    user: User,
    org_id: uuid.UUID,
    session: AsyncSession,
) -> OrganizationRole | None:
    """Helper: vrati ulogu user-a u danoj organizaciji ili None ako nije član."""
    membership = await session.scalar(
        select(OrganizationUser).where(
            OrganizationUser.user_id == user.id,
            OrganizationUser.organization_id == org_id,
        )
    )
    return membership.role if membership else None


def require_super_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    """Dep koji prepušta samo super admin-e (Marko). Koristi se na /admin/* rutama."""
    if not user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Pristup ograničen na super administratore.",
        )
    return user


def require_org_role(*allowed: OrganizationRole) -> Callable:
    """Factory dep koji prepušta samo članove org-a s jednom od dozvoljenih
    uloga. Super-admin uvijek prolazi. Vraća FastAPI Dependency callable.

    Primjer:
        @router.delete(...)
        async def delete_org(
            _: Annotated[User, Depends(require_org_role(OrganizationRole.OWNER))],
        ): ...
    """
    async def dependency(
        user: Annotated[User, Depends(get_current_user)],
        org: Annotated[Organization, Depends(get_current_organization)],
        session: Annotated[AsyncSession, Depends(get_session)],
    ) -> User:
        if user.is_super_admin:
            return user
        role = await get_user_role_in_org(user, org.id, session)
        if role is None or role not in allowed:
            roles_str = ", ".join(r.value for r in allowed)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Potrebna uloga: {roles_str}. Tvoja: {role.value if role else 'nije član'}.",
            )
        return user

    return dependency


def requires_module(module_code: str) -> Callable:
    """Factory dep: provjeri ima li trenutna organizacija aktivnu pretplatu
    na modul s `module_code` i nije li potrošila kvotu.

    Throws 402 Payment Required ako nema aktivne pretplate (semantika:
    "trebaš platiti pretplatu da bi koristio ovaj resurs").
    Throws 429 Too Many Requests ako je kvota potrošena.

    Primjer:
        @router.post("/documents/{id}/analyze")
        async def analyze(
            _: Annotated[Subscription, Depends(requires_module("don_analiza"))],
            ...
        ): ...
    """
    async def dependency(
        org: Annotated[Organization, Depends(get_current_organization)],
        session: Annotated[AsyncSession, Depends(get_session)],
    ) -> Subscription:
        now = datetime.now(timezone.utc)
        # Find module
        module = await session.scalar(
            select(Module).where(Module.code == module_code)
        )
        if not module:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Modul „{module_code}” nije definiran u sustavu.",
            )
        # Find active subscription
        subscription = await session.scalar(
            select(Subscription)
            .where(
                Subscription.organization_id == org.id,
                Subscription.module_id == module.id,
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.period_start <= now,
                Subscription.period_end >= now,
            )
            .order_by(Subscription.period_end.desc())
            .limit(1)
        )
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=(
                    f"Organizacija „{org.name}” nema aktivnu pretplatu na modul "
                    f"„{module.name}”. Aktiviraj pretplatu u postavkama."
                ),
            )
        # Kvota check je u service layeru (jer treba inc-ati UsageRecord)
        # — ovdje samo verificiramo da postoji aktivna pretplata.
        return subscription

    return dependency


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentOrganization = Annotated[Organization, Depends(get_current_organization)]
DbSession = Annotated[AsyncSession, Depends(get_session)]


__all__ = [
    "CurrentOrganization",
    "CurrentUser",
    "DbSession",
    "get_current_organization",
    "get_current_user",
    "get_user_role_in_org",
    "require_org_role",
    "require_super_admin",
    "requires_module",
    "select",
]
