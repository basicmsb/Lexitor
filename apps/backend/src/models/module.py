"""Module — proizvodni modul koji se može pretplatiti à la carte.

Trenutno: DON, Troskovnik, Zalbe, RAG search. Novi moduli dodaju se kao novi
redovi u tablici, ne kao enum u kodu (omogućuje kreiranje modula bez release-a).
"""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.session import Base, TimestampMixin


class Module(Base, TimestampMixin):
    __tablename__ = "modules"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Code — stabilna oznaka koja se koristi u kodu i decorator-ima
    # (npr. @requires_module("don_analiza"))
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Da li je modul javno dostupan (ili u beta/internal)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Sort order za UI prikaz (manji = prvi)
    sort_order: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
