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


class UserVerdict(str, enum.Enum):
    """User feedback on a Lexitor finding — does the user agree with it?
    `correct` confirms the finding, `incorrect` disputes it (and a
    comment explaining why is mandatory). null means no feedback yet."""

    CORRECT = "correct"
    INCORRECT = "incorrect"


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
    # Multiple Lexitor findings per stavka. Each entry is a dict with:
    # kind (e.g. "brand_lock"), status (per-finding severity),
    # explanation, suggestion, is_mock (true for random demo), citations
    # (list of {source, reference, snippet, url}). Item-level
    # explanation/suggestion/status are kept for backwards compat as
    # the aggregate (worst-status) finding.
    findings: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # User feedback on the finding (Phase A of the PDF-export workflow):
    # — user_verdict null → no feedback yet
    # — user_verdict CORRECT → user confirms the analyzer's finding
    # — user_verdict INCORRECT → user disputes; user_comment is mandatory
    # `include_in_pdf` controls whether this item appears in the
    # exported PDF report.
    user_verdict: Mapped[UserVerdict | None] = mapped_column(
        Enum(UserVerdict, name="user_verdict"),
        nullable=True,
    )
    user_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    include_in_pdf: Mapped[bool] = mapped_column(
        nullable=False, default=True, server_default="true",
    )
    # User-added findings — things the analyzer missed. Each entry is a
    # dict {id, kind, status, comment, created_at}. Kept separate from
    # `findings` (analyzer output) so the export endpoint can label them
    # as "LA propustio" (missed) vs "LA pronašao + verdict".
    user_added_findings: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # Override za `kind` ako parser pogriješi (npr. red "2.7. Demontaža…"
    # je section_header u parser-u, ali stvarno je stavka s podstavkama).
    # NULL = bez override-a (frontend koristi metadata.kind).
    user_kind_override: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )

    analysis: Mapped[Analysis] = relationship(back_populates="items")
    citations: Mapped[list[Citation]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )
