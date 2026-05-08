"""add_user_added_findings_to_analysis_items

Adds a `user_added_findings` JSONB column on analysis_items so the user
can mark findings that the LA missed (false negatives). Each entry is a
self-contained dict with id (uuid for delete operations), kind, status,
comment, created_at. These are kept separate from `findings` (which the
analyzer produced) so that the export endpoint can clearly show "LA
missed these" vs "LA found these and the user agreed/disagreed".

Revision ID: d6b3e4f5a207
Revises: c5a2b3d4e106
Create Date: 2026-05-08

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d6b3e4f5a207"
down_revision: str | None = "c5a2b3d4e106"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "analysis_items",
        sa.Column(
            "user_added_findings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("analysis_items", "user_added_findings")
