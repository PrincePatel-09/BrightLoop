"""snapshot company identity and currency on invoices

Revision ID: 0007_invoice_company_currency
Revises: 0006_settings
Create Date: 2026-10-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_invoice_company_currency"
down_revision: Union[str, Sequence[str], None] = "0006_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("company_name", sa.String(180), nullable=False, server_default="SubNexa"))
    op.add_column("invoices", sa.Column("currency_code", sa.String(3), nullable=False, server_default="INR"))


def downgrade() -> None:
    op.drop_column("invoices", "currency_code")
    op.drop_column("invoices", "company_name")
