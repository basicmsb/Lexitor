"""Organization — SaaS tenant entitet ("Tvrtka / Organizacija" u UI).

Obuhvaća sve subjekte koji koriste Lexitor: hrvatske tvrtke (d.o.o./d.d.),
ustanove (KBC, fakulteti, općine, ministarstva), kao i strane organizacije.
Svaki Organization plaća pretplatu i grupira N korisnika (`OrganizationUser`)
i N workspace-ova (Project).

Tipovi pristupa:
- Super Admin (User.is_super_admin=True): vidi sve Organizations
- Organization Owner / Admin: upravlja članovima, pretplatama, settings
- Organization Member: koristi module prema active subscriptions
- Organization Viewer: read-only
"""
from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.session import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.subscription import Subscription
    from src.models.usage_record import UsageRecord
    from src.models.user import User


class OrganizationType(str, enum.Enum):
    """Tip subjekta — utječe na billing i tax handling."""

    TVRTKA = "tvrtka"  # d.o.o., d.d., j.d.o.o.
    USTANOVA = "ustanova"  # KBC, fakulteti, javne ustanove
    OPCINA = "opcina"  # općina, grad, županija
    MINISTARSTVO = "ministarstvo"  # tijelo državne uprave
    OBRT = "obrt"  # obrt, samostalni
    UDRUGA = "udruga"  # udruga, zaklada
    STRANI = "strani"  # strana organizacija (bez OIB-a)
    OSTALO = "ostalo"


class OrganizationRole(str, enum.Enum):
    """Uloga unutar organizacije (per-org granular, ne globalno)."""

    OWNER = "owner"  # full pristup + brisanje organizacije + billing
    ADMIN = "admin"  # full pristup osim brisanja organizacije
    MEMBER = "member"  # koristi module, kreira analize
    VIEWER = "viewer"  # read-only pristup


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Slug za URL/identifikaciju (npr. "arhigon", "kbc-zagreb")
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    type: Mapped[OrganizationType] = mapped_column(
        Enum(OrganizationType, name="organization_type"),
        default=OrganizationType.TVRTKA,
        nullable=False,
    )
    # OIB — primarni jedinstveni identifikator za hrvatske subjekte.
    # Null za strane / još-bez-OIB-a. Nije unique jer može biti null više puta;
    # validacija jedinstvenosti se radi na app razini.
    oib: Mapped[str | None] = mapped_column(String(11), nullable=True, index=True)
    # Sjedište / adresa za fakture
    address: Mapped[str | None] = mapped_column(String(512), nullable=True)
    billing_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    # Logo za UI/PDF report (path do uploaded fajla)
    logo_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Stripe customer ID — null ako koristi manual billing
    stripe_customer_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)

    # Relacije
    members: Mapped[list["OrganizationUser"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan", lazy="selectin"
    )
    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan", lazy="selectin"
    )
    usage_records: Mapped[list["UsageRecord"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )


class OrganizationUser(Base, TimestampMixin):
    """M:N veza između User i Organization s ulogom po-organizaciji."""

    __tablename__ = "organization_users"
    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_user_org"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[OrganizationRole] = mapped_column(
        Enum(OrganizationRole, name="organization_role"),
        default=OrganizationRole.MEMBER,
        nullable=False,
    )
    # Tko je pozvao ovog usera (za audit)
    invited_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    user: Mapped["User"] = relationship(
        foreign_keys=[user_id], back_populates="memberships", lazy="selectin"
    )
    organization: Mapped[Organization] = relationship(
        back_populates="members", lazy="selectin"
    )
