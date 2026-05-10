"""UsageRecord — mjesečni brojač korištenja modula po Organization-u.

Jedan red po (organization, module, period_ym). Inkrementira se pri svakoj
analizi (DON / Troskovnik / Zalbe / RAG search). Koristi se za:
- Kvota enforcement (npr. 100 DON analiza/mj na Pro tier-u)
- Cost tracking (LLM trošak po company, za billing reconciliation)
- Admin dashboard (top usage, churn signali)
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.session import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.module import Module
    from src.models.organization import Organization


class UsageRecord(Base, TimestampMixin):
    __tablename__ = "usage_records"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "module_id", "period_ym",
            name="uq_org_module_period_ym",
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
    # Period u formatu "2026-05" (YYYY-MM)
    period_ym: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    # Broj izvršenih analiza/akcija u ovom periodu
    count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Akumulirani LLM trošak (USD, precision 4 decimala za male transakcije)
    llm_cost_usd: Mapped[float] = mapped_column(
        Numeric(precision=10, scale=4), default=0, nullable=False
    )

    organization: Mapped[Organization] = relationship(
        back_populates="usage_records", lazy="selectin"
    )
    module: Mapped[Module] = relationship(lazy="selectin")
