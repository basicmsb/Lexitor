from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.session import Base, TimestampMixin
from src.models.document import DocumentType

if TYPE_CHECKING:
    from src.models.document import Document
    from src.models.project import Project


class DocumentSet(Base, TimestampMixin):
    """Grupa povezanih fajlova jednog DON-a / nabave.

    Primjer: jedan DON sa EOJN-a sastoji se od više fajlova
    (Upute za ponuditelje.md, Kriteriji za odabir.md, prilozi.docx).
    DocumentSet ih grupira kroz `set_id` FK na svakom Document-u.
    """

    __tablename__ = "document_sets"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, name="document_type"), nullable=False,
    )

    project: Mapped[Project] = relationship(lazy="selectin")
    documents: Mapped[list[Document]] = relationship(
        back_populates="document_set",
        cascade="all, delete-orphan",
        order_by="Document.created_at",
    )
