"""track credit notes and payment refunds

Revision ID: 0018_credit_notes_refunds
Revises: 0017_company_scoped_discounts
Create Date: 2026-10-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0018_credit_notes_refunds"
down_revision: Union[str, Sequence[str], None] = "0017_company_scoped_discounts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("credited_amount", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.add_column("payments", sa.Column("refunded_amount", sa.Numeric(12, 2), nullable=False, server_default="0"))
    with op.batch_alter_table("invoices") as batch:
        batch.create_check_constraint("ck_invoices_paid_credit_limit", "credited_amount >= 0 AND amount_paid + credited_amount <= total_amount")
    with op.batch_alter_table("payments") as batch:
        batch.create_check_constraint("ck_payments_refund_limit", "refunded_amount >= 0 AND refunded_amount <= amount")
    op.create_table(
        "credit_notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("number", sa.String(32), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="issued"),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("voided_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("voided_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("amount > 0", name="ck_credit_notes_amount_positive"),
        sa.CheckConstraint("status IN ('issued', 'void')", name="ck_credit_notes_status"),
    )
    op.create_index("ix_credit_notes_company_id", "credit_notes", ["company_id"])
    op.create_index("ix_credit_notes_invoice_id", "credit_notes", ["invoice_id"])
    op.create_index("ix_credit_notes_status", "credit_notes", ["status"])
    op.create_index("uq_credit_notes_company_number", "credit_notes", ["company_id", "number"], unique=True)
    op.create_table(
        "payment_refunds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("payment_id", sa.Integer(), sa.ForeignKey("payments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("number", sa.String(32), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("reference", sa.String(120)),
        sa.Column("refunded_at", sa.Date(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("amount > 0", name="ck_payment_refunds_amount_positive"),
    )
    op.create_index("ix_payment_refunds_company_id", "payment_refunds", ["company_id"])
    op.create_index("ix_payment_refunds_payment_id", "payment_refunds", ["payment_id"])
    op.create_index("uq_payment_refunds_company_number", "payment_refunds", ["company_id", "number"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_payment_refunds_company_number", table_name="payment_refunds")
    op.drop_index("ix_payment_refunds_payment_id", table_name="payment_refunds")
    op.drop_index("ix_payment_refunds_company_id", table_name="payment_refunds")
    op.drop_table("payment_refunds")
    op.drop_index("uq_credit_notes_company_number", table_name="credit_notes")
    op.drop_index("ix_credit_notes_status", table_name="credit_notes")
    op.drop_index("ix_credit_notes_invoice_id", table_name="credit_notes")
    op.drop_index("ix_credit_notes_company_id", table_name="credit_notes")
    op.drop_table("credit_notes")
    with op.batch_alter_table("payments") as batch:
        batch.drop_constraint("ck_payments_refund_limit", type_="check")
        batch.drop_column("refunded_amount")
    with op.batch_alter_table("invoices") as batch:
        batch.drop_constraint("ck_invoices_paid_credit_limit", type_="check")
        batch.drop_column("credited_amount")
