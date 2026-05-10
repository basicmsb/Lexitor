from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.session import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.organization import OrganizationUser
    from src.models.project import Project


class UserRole(str, enum.Enum):
    """Legacy globalna uloga. Sad zamijenjena per-organization ulogama u
    OrganizationUser. Polje ostaje za backwards-compat dok ne migriramo
    sve postojeće veze. SuperAdmin (Marko) koristi `is_super_admin`."""

    USER = "user"
    ADMIN = "admin"
    OWNER = "owner"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # SuperAdmin globalna razina (samo Marko) — vidi/upravlja svim organizations
    is_super_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Legacy polja zadržana za migration period. Drop u sljedećoj migraciji.
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        default=UserRole.USER,
        nullable=False,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    project: Mapped[Project | None] = relationship(back_populates="users", lazy="selectin")
    # Membership u organizacijama — primary mechanism going forward
    memberships: Mapped[list[OrganizationUser]] = relationship(
        foreign_keys="OrganizationUser.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
