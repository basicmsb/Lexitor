"""add_document_sets_for_grouping

Dvoslojni model za DON: jedna stvarna nabava (npr. "JN-25/2026 Krupa")
sastoji se od više datoteka (Upute za ponuditelje, Kriteriji, Općg podaci,
prilozi). DocumentSet je grupa, Document je pojedinačni fajl s set_id FK.

set_id je nullable — postojeći Documents (troškovnici) ostaju single-file
i nemaju potrebu za setom. Nove DON multi-uploads kreiraju set + N docs.

Revision ID: g9e6d7c0b125
Revises: f8d5c6b9a014
Create Date: 2026-05-10
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM, UUID as PG_UUID


revision: str = "g9e6d7c0b125"
down_revision: str | None = "f8d5c6b9a014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_sets",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id", PG_UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column(
            "document_type",
            PG_ENUM(
                "TROSKOVNIK", "DON", "ZALBA", "OTHER",
                name="document_type", create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("now()"), nullable=False,
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "set_id", PG_UUID(as_uuid=True),
            sa.ForeignKey("document_sets.id", ondelete="SET NULL"),
            nullable=True, index=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("documents", "set_id")
    op.drop_table("document_sets")
