"""add company GST snapshots and financial-year invoice sequences

Revision ID: 0016_company_gst_invoice_sequences
Revises: 0015_razorpay_payment_attempts
Create Date: 2026-10-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0016_company_gst_invoice_sequences"
down_revision: Union[str, Sequence[str], None] = "0015_razorpay_payment_attempts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_invoices_number", table_name="invoices")
    op.create_index("uq_invoices_company_number", "invoices", ["company_id", "number"], unique=True)
    op.add_column("customers", sa.Column("gstin", sa.String(20), nullable=True))
    op.add_column("customers", sa.Column("state_code", sa.String(12), nullable=True))
    for name, kind in (
        ("seller_address", sa.Text()), ("seller_email", sa.String(255)), ("seller_phone", sa.String(40)),
        ("seller_gstin", sa.String(20)), ("seller_state_name", sa.String(80)), ("seller_state_code", sa.String(2)),
        ("customer_gstin", sa.String(20)), ("customer_state_code", sa.String(2)), ("payment_terms", sa.String(120)),
    ):
        op.add_column("invoices", sa.Column(name, kind, nullable=True))
    op.create_table(
        "invoice_sequences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("fiscal_year", sa.String(7), nullable=False),
        sa.Column("next_number", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("company_id", "fiscal_year", name="uq_invoice_sequence_company_year"),
        sa.CheckConstraint("next_number > 0", name="ck_invoice_sequence_next_positive"),
    )


def downgrade() -> None:
    op.drop_table("invoice_sequences")
    for name in ("payment_terms", "customer_state_code", "customer_gstin", "seller_state_code", "seller_state_name", "seller_gstin", "seller_phone", "seller_email", "seller_address"):
        op.drop_column("invoices", name)
    op.drop_column("customers", "state_code")
    op.drop_column("customers", "gstin")
    op.drop_index("uq_invoices_company_number", table_name="invoices")
    op.create_index("ix_invoices_number", "invoices", ["number"], unique=True)
