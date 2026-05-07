from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.session import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.analysis import AnalysisItem


class CitationSource(str, enum.Enum):
    ZJN = "zjn"
    DKOM = "dkom"
    VUS = "vus"
    EU = "eu"
    OTHER = "other"


class Citation(Base, TimestampMixin):
    __tablename__ = "citations"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("analysis_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source: Mapped[CitationSource] = mapped_column(
        Enum(CitationSource, name="citation_source"),
        nullable=False,
    )
    reference: Mapped[str] = mapped_column(String(512), nullable=False)
    snippet: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    item: Mapped[AnalysisItem] = relationship(back_populates="citations")
