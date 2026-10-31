"""add quotations and subscriptions

Revision ID: 0003_sales
Revises: 0002_catalog
Create Date: 2026-10-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_sales"
down_revision: Union[str, Sequence[str], None] = "0002_catalog"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "quotations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("number", sa.String(32), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("product_name", sa.String(180), nullable=False),
        sa.Column("plan_name", sa.String(180), nullable=False),
        sa.Column("billing_interval", sa.String(16), nullable=False),
        sa.Column("interval_count", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("valid_until", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('draft', 'sent', 'accepted', 'converted', 'expired', 'cancelled')", name="ck_quotations_status"),
        sa.CheckConstraint("quantity > 0 AND unit_price >= 0", name="ck_quotations_amounts"),
    )
    op.create_index("ix_quotations_number", "quotations", ["number"], unique=True)
    op.create_index("ix_quotations_customer_id", "quotations", ["customer_id"])
    op.create_index("ix_quotations_status", "quotations", ["status"])

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("number", sa.String(32), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quotation_id", sa.Integer(), sa.ForeignKey("quotations.id", ondelete="RESTRICT"), unique=True),
        sa.Column("product_name", sa.String(180), nullable=False),
        sa.Column("plan_name", sa.String(180), nullable=False),
        sa.Column("billing_interval", sa.String(16), nullable=False),
        sa.Column("interval_count", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("next_billing_date", sa.Date(), nullable=False),
        sa.Column("cancelled_at", sa.Date()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('active', 'paused', 'cancelled', 'expired')", name="ck_subscriptions_status"),
        sa.CheckConstraint("quantity > 0 AND unit_price >= 0", name="ck_subscriptions_amounts"),
    )
    op.create_index("ix_subscriptions_number", "subscriptions", ["number"], unique=True)
    op.create_index("ix_subscriptions_customer_id", "subscriptions", ["customer_id"])
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"])
    op.create_index("ix_subscriptions_next_billing_date", "subscriptions", ["next_billing_date"])


def downgrade() -> None:
    op.drop_table("subscriptions")
    op.drop_index("ix_quotations_status", table_name="quotations")
    op.drop_index("ix_quotations_customer_id", table_name="quotations")
    op.drop_index("ix_quotations_number", table_name="quotations")
    op.drop_table("quotations")
