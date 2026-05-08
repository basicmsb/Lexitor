from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.session import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.document import Document
    from src.models.user import User


class Project(Base, TimestampMixin):
    """Workspace / organization tenant. Each user belongs to one project."""

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    # Optional path to a project logo file (uploaded to local storage).
    # Used by the PDF report header alongside the Lexitor wordmark. Null
    # → PDF falls back to rendering the project name as text.
    logo_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    users: Mapped[list[User]] = relationship(back_populates="project", cascade="all, delete-orphan")
    documents: Mapped[list[Document]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
