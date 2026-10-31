"""add catalogue products and subscription plans

Revision ID: 0002_catalog
Revises: 0001_phase1_auth
Create Date: 2026-10-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_catalog"
down_revision: Union[str, Sequence[str], None] = "0001_phase1_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("sku", sa.String(length=80), nullable=False),
        sa.Column("product_type", sa.String(length=24), nullable=False),
        sa.Column("sales_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("cost_price", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("product_type IN ('service', 'physical', 'digital')", name="ck_products_type"),
        sa.CheckConstraint("sales_price >= 0 AND cost_price >= 0", name="ck_products_prices_nonnegative"),
    )
    op.create_index("ix_products_sku", "products", ["sku"], unique=True)

    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("billing_interval", sa.String(length=16), nullable=False),
        sa.Column("interval_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("billing_interval IN ('day', 'week', 'month', 'year')", name="ck_plans_interval"),
        sa.CheckConstraint("price >= 0", name="ck_plans_price_nonnegative"),
        sa.CheckConstraint("interval_count >= 1", name="ck_plans_interval_count"),
    )
    op.create_index("ix_plans_product_id", "plans", ["product_id"])


def downgrade() -> None:
    op.drop_table("plans")
    op.drop_index("ix_products_sku", table_name="products")
    op.drop_table("products")
