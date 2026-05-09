"""add_troskovnik_type_to_documents

Adds enum kolonu `troskovnik_type` na documents tablicu. Korisnik bira pri
uploadu: ponudbeni (jed. cijena MORA biti prazna — ponuditelj je popunjava)
ili procjena (jed. cijena MORA biti popunjena — projektant procjenjuje
budžet). "nepoznato" je default fallback. Ove vrijednosti utječu na to
da li `rule_missing_cijena` i `rule_zero_unit_price` fire-aju.

Revision ID: e7c4f5a608b2
Revises: d6b3e4f5a207
Create Date: 2026-05-08

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "e7c4f5a608b2"
down_revision: str | None = "d6b3e4f5a207"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Konzistentno s document_type / user_role: SQLAlchemy by-default
    # storeira enum.NAME u Postgresu, pa labels moraju biti UPPERCASE.
    troskovnik_type_enum = sa.Enum(
        "PONUDBENI", "PROCJENA", "NEPOZNATO",
        name="troskovnik_type",
    )
    troskovnik_type_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "documents",
        sa.Column(
            "troskovnik_type",
            troskovnik_type_enum,
            nullable=False,
            server_default="NEPOZNATO",
        ),
    )


def downgrade() -> None:
    op.drop_column("documents", "troskovnik_type")
    sa.Enum(name="troskovnik_type").drop(op.get_bind(), checkfirst=True)
