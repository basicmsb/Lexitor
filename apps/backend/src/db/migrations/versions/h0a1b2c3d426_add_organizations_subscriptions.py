"""add_organizations_modules_subscriptions

Phase 1 SaaS multi-tenant arhitekture (vidi `docs/SAAS-ARCHITECTURE.md`).

Stvara:
- `organizations` — tvrtka/ustanova ("Tvrtka / Organizacija" na UI-u)
- `organization_users` — M:N user-organization s ulogom po-org
- `modules` — proizvodni moduli (don_analiza, troskovnik, zalbe, rag_search)
- `subscriptions` — pretplate organizacije na modul (tier + period)
- `usage_records` — mjesečni brojač korištenja

Postojeći `projects` dobiva `organization_id` (nullable za migration period —
postojeći single-tenant projects ostaju bez org-a dok ručno ne migriraju).
Postojeći `users` dobivaju `is_super_admin` flag.

Revision ID: h0a1b2c3d426
Revises: g9e6d7c0b125
Create Date: 2026-05-11
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM, UUID as PG_UUID


revision: str = "h0a1b2c3d426"
down_revision: str | None = "g9e6d7c0b125"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ORGANIZATION_TYPE_VALUES = (
    "tvrtka", "ustanova", "opcina", "ministarstvo",
    "obrt", "udruga", "strani", "ostalo",
)
ORGANIZATION_ROLE_VALUES = ("owner", "admin", "member", "viewer")
SUBSCRIPTION_TIER_VALUES = ("free_trial", "starter", "pro", "enterprise")
SUBSCRIPTION_STATUS_VALUES = ("active", "expired", "cancelled", "paused")
SUBSCRIPTION_SOURCE_VALUES = ("stripe", "manual", "trial")


def upgrade() -> None:
    # Enums (kreirati prije tablica)
    org_type = PG_ENUM(*ORGANIZATION_TYPE_VALUES, name="organization_type", create_type=True)
    org_role = PG_ENUM(*ORGANIZATION_ROLE_VALUES, name="organization_role", create_type=True)
    sub_tier = PG_ENUM(*SUBSCRIPTION_TIER_VALUES, name="subscription_tier", create_type=True)
    sub_status = PG_ENUM(*SUBSCRIPTION_STATUS_VALUES, name="subscription_status", create_type=True)
    sub_source = PG_ENUM(*SUBSCRIPTION_SOURCE_VALUES, name="subscription_source", create_type=True)
    org_type.create(op.get_bind(), checkfirst=True)
    org_role.create(op.get_bind(), checkfirst=True)
    sub_tier.create(op.get_bind(), checkfirst=True)
    sub_status.create(op.get_bind(), checkfirst=True)
    sub_source.create(op.get_bind(), checkfirst=True)

    # --- organizations ---
    op.create_table(
        "organizations",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column(
            "type",
            PG_ENUM(*ORGANIZATION_TYPE_VALUES, name="organization_type", create_type=False),
            nullable=False, server_default="tvrtka",
        ),
        sa.Column("oib", sa.String(length=11), nullable=True),
        sa.Column("address", sa.String(length=512), nullable=True),
        sa.Column("billing_email", sa.String(length=320), nullable=True),
        sa.Column("logo_path", sa.String(length=512), nullable=True),
        sa.Column("stripe_customer_id", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)
    op.create_index("ix_organizations_oib", "organizations", ["oib"])
    op.create_index("ix_organizations_stripe_customer_id", "organizations", ["stripe_customer_id"])

    # --- organization_users ---
    op.create_table(
        "organization_users",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", PG_UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id", PG_UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            PG_ENUM(*ORGANIZATION_ROLE_VALUES, name="organization_role", create_type=False),
            nullable=False, server_default="member",
        ),
        sa.Column(
            "invited_by_user_id", PG_UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "organization_id", name="uq_user_org"),
    )
    op.create_index("ix_organization_users_user_id", "organization_users", ["user_id"])
    op.create_index("ix_organization_users_organization_id", "organization_users", ["organization_id"])

    # --- modules ---
    op.create_table(
        "modules",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_modules_code", "modules", ["code"], unique=True)

    # Seed default modula
    modules_table = sa.table(
        "modules",
        sa.column("id", PG_UUID(as_uuid=True)),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("sort_order", sa.Integer),
    )
    import uuid as _uuid
    op.bulk_insert(modules_table, [
        {
            "id": _uuid.uuid4(),
            "code": "don_analiza",
            "name": "DON analiza",
            "description": "Detekcija povreda ZJN u Dokumentaciji o nabavi (brand_lock, kratki_rok, vague_kriterij, …).",
            "sort_order": 10,
        },
        {
            "id": _uuid.uuid4(),
            "code": "troskovnik",
            "name": "Troškovnik analiza",
            "description": "Matematska + leksička validacija Arhigon/Excel troškovnika.",
            "sort_order": 20,
        },
        {
            "id": _uuid.uuid4(),
            "code": "zalbe",
            "name": "Žalbe asistent",
            "description": "Generira tekst žalbe DKOM-u iz presedana, predviđa success rate.",
            "sort_order": 30,
        },
        {
            "id": _uuid.uuid4(),
            "code": "rag_search",
            "name": "Pretraga pravne baze",
            "description": "Pitanja o ZJN/DKOM/Pravilnicima u prirodnom jeziku.",
            "sort_order": 40,
        },
    ])

    # --- subscriptions ---
    op.create_table(
        "subscriptions",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id", PG_UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "module_id", PG_UUID(as_uuid=True),
            sa.ForeignKey("modules.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "tier",
            PG_ENUM(*SUBSCRIPTION_TIER_VALUES, name="subscription_tier", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            PG_ENUM(*SUBSCRIPTION_STATUS_VALUES, name="subscription_status", create_type=False),
            nullable=False, server_default="active",
        ),
        sa.Column(
            "source",
            PG_ENUM(*SUBSCRIPTION_SOURCE_VALUES, name="subscription_source", create_type=False),
            nullable=False, server_default="manual",
        ),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("quota_override", sa.Integer(), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=80), nullable=True),
        sa.Column("notes", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "organization_id", "module_id", "period_start",
            name="uq_org_module_period",
        ),
    )
    op.create_index("ix_subscriptions_organization_id", "subscriptions", ["organization_id"])
    op.create_index("ix_subscriptions_module_id", "subscriptions", ["module_id"])
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"])
    op.create_index("ix_subscriptions_stripe_subscription_id", "subscriptions", ["stripe_subscription_id"])

    # --- usage_records ---
    op.create_table(
        "usage_records",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id", PG_UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "module_id", PG_UUID(as_uuid=True),
            sa.ForeignKey("modules.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("period_ym", sa.String(length=7), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("llm_cost_usd", sa.Numeric(precision=10, scale=4), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "organization_id", "module_id", "period_ym",
            name="uq_org_module_period_ym",
        ),
    )
    op.create_index("ix_usage_records_organization_id", "usage_records", ["organization_id"])
    op.create_index("ix_usage_records_module_id", "usage_records", ["module_id"])
    op.create_index("ix_usage_records_period_ym", "usage_records", ["period_ym"])

    # --- alter existing tables ---
    # users: add is_super_admin
    op.add_column(
        "users",
        sa.Column("is_super_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # users.project_id: make nullable (legacy, postaje opcionalno tijekom migration perioda)
    op.alter_column("users", "project_id", nullable=True)

    # projects: add organization_id FK (nullable)
    op.add_column(
        "projects",
        sa.Column("organization_id", PG_UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_projects_organization_id",
        "projects", "organizations",
        ["organization_id"], ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_projects_organization_id", "projects", ["organization_id"])


def downgrade() -> None:
    # Drop user columns
    op.alter_column("users", "project_id", nullable=False)
    op.drop_column("users", "is_super_admin")

    # Drop projects.organization_id
    op.drop_index("ix_projects_organization_id", table_name="projects")
    op.drop_constraint("fk_projects_organization_id", "projects", type_="foreignkey")
    op.drop_column("projects", "organization_id")

    # Drop new tables (redoslijed bitan zbog FK)
    op.drop_table("usage_records")
    op.drop_table("subscriptions")
    op.drop_table("modules")
    op.drop_table("organization_users")
    op.drop_table("organizations")

    # Drop enums
    for enum_name in (
        "subscription_source", "subscription_status", "subscription_tier",
        "organization_role", "organization_type",
    ):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
