"""add_project_logo_path

Adds optional `logo_path` column on projects so each tenant can have a
logo embedded in PDF reports next to the Lexitor wordmark.

Revision ID: b4e1d2a91f3c
Revises: a3f8c0d5e201
Create Date: 2026-05-08

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "b4e1d2a91f3c"
down_revision: str | None = "a3f8c0d5e201"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("logo_path", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("projects", "logo_path")
