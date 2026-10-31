"""add company tenancy foundation

Revision ID: 0011_companies_user_tenancy
Revises: 0010_plan_subscription_features
Create Date: 2026-10-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011_companies_user_tenancy"
down_revision: Union[str, Sequence[str], None] = "0010_plan_subscription_features"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("legal_name", sa.String(180)),
        sa.Column("slug", sa.String(80), nullable=False, unique=True),
        sa.Column("email", sa.String(255)),
        sa.Column("phone", sa.String(40)),
        sa.Column("address", sa.Text()),
        sa.Column("tax_id", sa.String(80)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_companies_slug", "companies", ["slug"], unique=True)
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", name="fk_users_company_id", ondelete="SET NULL")))
    op.create_index("ix_users_company_id", "users", ["company_id"])


def downgrade() -> None:
    op.drop_index("ix_users_company_id", table_name="users")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("company_id")
    op.drop_index("ix_companies_slug", table_name="companies")
    op.drop_table("companies")
