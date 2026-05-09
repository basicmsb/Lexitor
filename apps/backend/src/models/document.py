from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.session import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.analysis import Analysis
    from src.models.project import Project
    from src.models.user import User


class DocumentType(str, enum.Enum):
    TROSKOVNIK = "troskovnik"
    DON = "don"
    ZALBA = "zalba"
    OTHER = "other"


class TroskovnikType(str, enum.Enum):
    """Tip troškovnika određuje pravila za "Jediničnu cijenu":
    - PONUDBENI: jed. cijena MORA biti prazna (popunjava ponuditelj)
    - PROCJENA: jed. cijena MORA biti popunjena (projektantska procjena)
    - NEPOZNATO: tip nije specificiran — rules ostaju oprezni (ne fire-aju
      missing_cijena false-positive ali ne preskaču ni za stvarne procjene)"""

    PONUDBENI = "ponudbeni"
    PROCJENA = "procjena"
    NEPOZNATO = "nepoznato"


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, name="document_type"),
        default=DocumentType.OTHER,
        nullable=False,
    )
    troskovnik_type: Mapped[TroskovnikType] = mapped_column(
        Enum(TroskovnikType, name="troskovnik_type"),
        default=TroskovnikType.NEPOZNATO,
        # SA storeira enum.name (uppercase). Konzistentno s document_type.
        server_default=TroskovnikType.NEPOZNATO.name,
        nullable=False,
    )

    project: Mapped[Project] = relationship(back_populates="documents", lazy="selectin")
    uploaded_by: Mapped[User | None] = relationship(lazy="selectin")
    analyses: Mapped[list[Analysis]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="Analysis.created_at.desc()",
    )
