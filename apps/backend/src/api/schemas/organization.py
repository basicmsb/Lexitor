"""Pydantic schemas za Organization, OrganizationUser i povezane operacije."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

# Enum aliasi za jasniju API površinu
OrganizationTypeLiteral = Literal[
    "tvrtka", "ustanova", "opcina", "ministarstvo",
    "obrt", "udruga", "strani", "ostalo",
]
OrganizationRoleLiteral = Literal["owner", "admin", "member", "viewer"]


class OrganizationCreate(BaseModel):
    """Zahtjev za kreiranje nove organizacije (kroz registraciju ili admin panel)."""

    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9-]+$")
    type: OrganizationTypeLiteral = "tvrtka"
    oib: str | None = Field(default=None, min_length=11, max_length=11, pattern=r"^\d{11}$")
    address: str | None = Field(default=None, max_length=512)
    billing_email: EmailStr | None = None


class OrganizationUpdate(BaseModel):
    """Patch — sva polja opcionalna."""

    name: str | None = Field(default=None, min_length=2, max_length=255)
    type: OrganizationTypeLiteral | None = None
    oib: str | None = Field(default=None, pattern=r"^\d{11}$")
    address: str | None = Field(default=None, max_length=512)
    billing_email: EmailStr | None = None


class OrganizationPublic(BaseModel):
    """Public view — što vraćamo na API."""

    id: uuid.UUID
    name: str
    slug: str
    type: OrganizationTypeLiteral
    oib: str | None
    address: str | None
    billing_email: str | None
    logo_path: str | None
    has_stripe: bool  # bool umjesto pravog stripe ID (sigurnost)
    created_at: datetime
    updated_at: datetime


class OrganizationUserPublic(BaseModel):
    """Član organizacije s ulogom."""

    id: uuid.UUID
    user_id: uuid.UUID
    organization_id: uuid.UUID
    role: OrganizationRoleLiteral
    user_email: str
    user_full_name: str | None
    joined_at: datetime


class OrganizationMembershipInvite(BaseModel):
    """Pozovi novog člana u organizaciju."""

    email: EmailStr
    role: OrganizationRoleLiteral = "member"


class OrganizationMembershipUpdate(BaseModel):
    """Promijeni ulogu postojećem članu."""

    role: OrganizationRoleLiteral
