"""add_user_feedback_to_analysis_items

Adds three columns supporting Phase A of the PDF-export workflow:
- user_verdict (enum correct/incorrect, nullable)
- user_comment (text, mandatory in app logic when verdict=incorrect)
- include_in_pdf (bool, default true)

Revision ID: a3f8c0d5e201
Revises: bee2d1e57ac0
Create Date: 2026-05-08

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "a3f8c0d5e201"
down_revision: str | None = "bee2d1e57ac0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


user_verdict_enum = sa.Enum("correct", "incorrect", name="user_verdict")


def upgrade() -> None:
    user_verdict_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "analysis_items",
        sa.Column("user_verdict", user_verdict_enum, nullable=True),
    )
    op.add_column(
        "analysis_items",
        sa.Column("user_comment", sa.Text(), nullable=True),
    )
    op.add_column(
        "analysis_items",
        sa.Column(
            "include_in_pdf",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("analysis_items", "include_in_pdf")
    op.drop_column("analysis_items", "user_comment")
    op.drop_column("analysis_items", "user_verdict")
    user_verdict_enum.drop(op.get_bind(), checkfirst=True)
