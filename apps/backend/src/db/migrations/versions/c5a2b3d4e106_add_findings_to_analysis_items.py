"""add_findings_to_analysis_items

Adds a `findings` JSONB column on analysis_items so each stavka can carry
multiple Lexitor nalaza (brand_lock + arithmetic + missing_jm etc.) instead
of being limited to a single explanation/suggestion. Each finding is a
self-contained dict with kind, status, explanation, suggestion, is_mock,
citations.

The legacy explanation/suggestion/status columns stay — they hold the
"primary" / aggregate finding for backward compat.

Revision ID: c5a2b3d4e106
Revises: b4e1d2a91f3c
Create Date: 2026-05-08

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c5a2b3d4e106"
down_revision: str | None = "b4e1d2a91f3c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "analysis_items",
        sa.Column(
            "findings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("analysis_items", "findings")
