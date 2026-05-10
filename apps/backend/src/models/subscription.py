"""Subscription — pretplata Organization-a na pojedini Module.

Jedna Organization može imati N subscriptions (jedna po modulu). Subscription
ima tier (Starter/Pro/Enterprise/FreeTrial) i period (start/end). UsageRecord
prati koliko se modul koristi u tekućem mjesecu.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.session import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.module import Module
    from src.models.organization import Organization


class SubscriptionTier(str, enum.Enum):
    """Tier modula. Free trial = 30 dana s ograničenom kvotom (npr. 3 DON
    analize). Starter/Pro/Enterprise = naplaceni planovi s rastucim kvotama."""

    FREE_TRIAL = "free_trial"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"  # korisnik otkazao, vrijedi do period_end
    PAUSED = "paused"  # admin-only pauziranje


class SubscriptionSource(str, enum.Enum):
    """Odakle dolazi subscription — utječe na renewal i invoice logiku."""

    STRIPE = "stripe"  # auto-renewal kroz Stripe
    MANUAL = "manual"  # Marko ručno kreirao (Enterprise)
    TRIAL = "trial"  # auto-kreiran pri registraciji


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"
    __table_args__ = (
        # Jedna aktivna subscription po (organization, module) — preklapanja
        # rješavamo na app razini (završi staru pri novom upgrade-u).
        UniqueConstraint(
            "organization_id", "module_id", "period_start",
            name="uq_org_module_period",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    module_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("modules.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    tier: Mapped[SubscriptionTier] = mapped_column(
        Enum(SubscriptionTier, name="subscription_tier"),
        nullable=False,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, name="subscription_status"),
        default=SubscriptionStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    source: Mapped[SubscriptionSource] = mapped_column(
        Enum(SubscriptionSource, name="subscription_source"),
        default=SubscriptionSource.MANUAL,
        nullable=False,
    )
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Quota override — ako None, koristi se default za tier (centralna konfiguracija)
    quota_override: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Stripe ID za autosync
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(80), nullable=True, index=True
    )
    # Slobodno polje za bilješke (Marko: "ugovor potpisan 2026-05-01, manual invoice")
    notes: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    organization: Mapped[Organization] = relationship(
        back_populates="subscriptions", lazy="selectin"
    )
    module: Mapped[Module] = relationship(lazy="selectin")
