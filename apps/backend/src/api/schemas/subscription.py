"""Pydantic schemas za Module, Subscription, UsageRecord."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

SubscriptionTierLiteral = Literal["free_trial", "starter", "pro", "enterprise"]
SubscriptionStatusLiteral = Literal["active", "expired", "cancelled", "paused"]
SubscriptionSourceLiteral = Literal["stripe", "manual", "trial"]


# ---------------------------------------------------------------------------
# Module

class ModulePublic(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None
    is_public: bool
    sort_order: int


# ---------------------------------------------------------------------------
# Subscription

class SubscriptionCreate(BaseModel):
    """Super Admin kreira manualnu pretplatu (Enterprise) ili sistem kreira
    trial automatski pri registraciji."""

    organization_id: uuid.UUID
    module_code: str  # "don_analiza", "troskovnik", …
    tier: SubscriptionTierLiteral
    period_start: datetime
    period_end: datetime
    source: SubscriptionSourceLiteral = "manual"
    quota_override: int | None = None
    notes: str | None = Field(default=None, max_length=1024)


class SubscriptionUpdate(BaseModel):
    """Patch — npr. produžiti period, promijeniti tier."""

    tier: SubscriptionTierLiteral | None = None
    period_end: datetime | None = None
    status: SubscriptionStatusLiteral | None = None
    quota_override: int | None = None
    notes: str | None = Field(default=None, max_length=1024)


class SubscriptionPublic(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    module: ModulePublic
    tier: SubscriptionTierLiteral
    status: SubscriptionStatusLiteral
    source: SubscriptionSourceLiteral
    period_start: datetime
    period_end: datetime
    quota_override: int | None
    notes: str | None
    is_active: bool  # computed: status=active AND period_end > now
    current_usage: int  # computed: UsageRecord za tekući mjesec
    quota_effective: int  # computed: quota_override ili tier default


# ---------------------------------------------------------------------------
# UsageRecord

class UsageRecordPublic(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    module: ModulePublic
    period_ym: str  # "2026-05"
    count: int
    llm_cost_usd: Decimal


class OrganizationUsageSummary(BaseModel):
    """Sumar svih usage record-a za organizaciju + period filter.
    Vraća se na dashboard-u (per company i super admin)."""

    organization_id: uuid.UUID
    period_ym: str
    records: list[UsageRecordPublic]
    total_count: int  # zbroj count-ova
    total_cost_usd: Decimal
