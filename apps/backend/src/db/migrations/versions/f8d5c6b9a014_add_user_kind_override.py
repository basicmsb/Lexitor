"""add_user_kind_override_to_analysis_items

Korisnik može override-ati `kind` (auto-detektiran tip elementa) ako
parser pogriješi. Primjer: parser je rekao "section_header" za red
"2.7. Demontaža postojeće vanjske stolarije", ali to je zapravo
**stavka** s 3 numerirane podstavke. UI dropdown na svakoj kartici
omogućuje korisniku da reklasificira; spremamo u ovo polje.

Vrijednosti su iste kao `metadata.kind` (stavka, opci_uvjeti, tekst,
section_header, …) ili NULL ako nema override-a.

Revision ID: f8d5c6b9a014
Revises: e7c4f5a608b2
Create Date: 2026-05-10

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "f8d5c6b9a014"
down_revision: str | None = "e7c4f5a608b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "analysis_items",
        sa.Column("user_kind_override", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("analysis_items", "user_kind_override")
