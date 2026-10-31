"""add verified online payment attempts

Revision ID: 0015_razorpay_payment_attempts
Revises: 0014_subscription_change_requests
Create Date: 2026-10-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0015_razorpay_payment_attempts"
down_revision: Union[str, Sequence[str], None] = "0014_subscription_change_requests"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payment_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("payment_record_id", sa.Integer(), sa.ForeignKey("payments.id", ondelete="SET NULL"), unique=True),
        sa.Column("gateway_order_id", sa.String(48), nullable=False, unique=True),
        sa.Column("gateway_payment_id", sa.String(48), unique=True),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency_code", sa.String(3), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("amount_minor > 0", name="ck_payment_attempts_amount_positive"),
        sa.CheckConstraint("status IN ('pending', 'paid', 'failed', 'captured_unapplied')", name="ck_payment_attempts_status"),
    )
    op.create_index("ix_payment_attempts_company_id", "payment_attempts", ["company_id"])
    op.create_index("ix_payment_attempts_customer_id", "payment_attempts", ["customer_id"])
    op.create_index("ix_payment_attempts_invoice_id", "payment_attempts", ["invoice_id"])
    op.create_index("ix_payment_attempts_gateway_order_id", "payment_attempts", ["gateway_order_id"], unique=True)
    op.create_index("ix_payment_attempts_status", "payment_attempts", ["status"])


def downgrade() -> None:
    op.drop_index("ix_payment_attempts_status", table_name="payment_attempts")
    op.drop_index("ix_payment_attempts_gateway_order_id", table_name="payment_attempts")
    op.drop_index("ix_payment_attempts_invoice_id", table_name="payment_attempts")
    op.drop_index("ix_payment_attempts_customer_id", table_name="payment_attempts")
    op.drop_index("ix_payment_attempts_company_id", table_name="payment_attempts")
    op.drop_table("payment_attempts")
