from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.session import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.citation import Citation
    from src.models.document import Document


class AnalysisStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"


class AnalysisItemStatus(str, enum.Enum):
    OK = "ok"
    WARN = "warn"
    FAIL = "fail"
    NEUTRAL = "neutral"
    ACCEPTED = "accepted"
    UNCERTAIN = "uncertain"


class Analysis(Base, TimestampMixin):
    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus, name="analysis_status"),
        default=AnalysisStatus.PENDING,
        nullable=False,
        index=True,
    )
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    document: Mapped[Document] = relationship(back_populates="analyses", lazy="selectin")
    items: Mapped[list[AnalysisItem]] = relationship(
        back_populates="analysis",
        cascade="all, delete-orphan",
        order_by="AnalysisItem.position",
    )


class AnalysisItem(Base, TimestampMixin):
    __tablename__ = "analysis_items"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str | None] = mapped_column(Text, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[AnalysisItemStatus] = mapped_column(
        Enum(AnalysisItemStatus, name="analysis_item_status"),
        default=AnalysisItemStatus.NEUTRAL,
        nullable=False,
    )
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    highlights: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    analysis: Mapped[Analysis] = relationship(back_populates="items")
    citations: Mapped[list[Citation]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )
