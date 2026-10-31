"""add tax and discount rules with invoice snapshots

Revision ID: 0005_pricing_rules
Revises: 0004_billing
Create Date: 2026-10-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_pricing_rules"
down_revision: Union[str, Sequence[str], None] = "0004_billing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tax_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("rate_percent", sa.Numeric(5, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("rate_percent >= 0 AND rate_percent <= 100", name="ck_tax_rules_rate"),
    )
    op.create_table(
        "discounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("discount_type", sa.String(16), nullable=False),
        sa.Column("value", sa.Numeric(12, 2), nullable=False),
        sa.Column("minimum_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("starts_at", sa.Date()),
        sa.Column("ends_at", sa.Date()),
        sa.Column("usage_limit", sa.Integer()),
        sa.Column("times_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("discount_type IN ('fixed', 'percentage')", name="ck_discounts_type"),
        sa.CheckConstraint("value > 0", name="ck_discounts_value"),
        sa.CheckConstraint("minimum_amount >= 0", name="ck_discounts_minimum"),
        sa.CheckConstraint("usage_limit IS NULL OR usage_limit > 0", name="ck_discounts_usage_limit"),
    )
    op.create_index("ix_discounts_code", "discounts", ["code"], unique=True)

    with op.batch_alter_table("quotations") as batch_op:
        batch_op.add_column(sa.Column("discount_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_quotations_discount_id", "discounts", ["discount_id"], ["id"], ondelete="RESTRICT")
    op.add_column("quotations", sa.Column("discount_code", sa.String(40)))
    op.add_column("quotations", sa.Column("discount_type", sa.String(16)))
    op.add_column("quotations", sa.Column("discount_value", sa.Numeric(12, 2)))
    op.add_column("quotations", sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False, server_default="0"))

    with op.batch_alter_table("subscriptions") as batch_op:
        batch_op.add_column(sa.Column("discount_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_subscriptions_discount_id", "discounts", ["discount_id"], ["id"], ondelete="RESTRICT")
    op.add_column("subscriptions", sa.Column("discount_code", sa.String(40)))
    op.add_column("subscriptions", sa.Column("discount_type", sa.String(16)))
    op.add_column("subscriptions", sa.Column("discount_value", sa.Numeric(12, 2)))
    op.add_column("subscriptions", sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False, server_default="0"))

    op.add_column("invoices", sa.Column("tax_details", sa.JSON()))


def downgrade() -> None:
    op.drop_column("invoices", "tax_details")
    op.drop_column("subscriptions", "discount_amount")
    op.drop_column("subscriptions", "discount_value")
    op.drop_column("subscriptions", "discount_type")
    op.drop_column("subscriptions", "discount_code")
    with op.batch_alter_table("subscriptions") as batch_op:
        batch_op.drop_constraint("fk_subscriptions_discount_id", type_="foreignkey")
        batch_op.drop_column("discount_id")
    op.drop_column("quotations", "discount_amount")
    op.drop_column("quotations", "discount_value")
    op.drop_column("quotations", "discount_type")
    op.drop_column("quotations", "discount_code")
    with op.batch_alter_table("quotations") as batch_op:
        batch_op.drop_constraint("fk_quotations_discount_id", type_="foreignkey")
        batch_op.drop_column("discount_id")
    op.drop_index("ix_discounts_code", table_name="discounts")
    op.drop_table("discounts")
    op.drop_table("tax_rules")
