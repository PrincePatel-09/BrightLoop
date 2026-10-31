"""snapshot recurring quotation and invoice line items

Revision ID: 0021_recurring_line_items
Revises: 0020_quotation_templates
Create Date: 2026-10-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0021_recurring_line_items"
down_revision: Union[str, Sequence[str], None] = "0020_quotation_templates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in ("quotations", "quotation_templates", "subscriptions", "invoices"):
        op.add_column(table, sa.Column("line_items", sa.JSON(), nullable=True))


def downgrade() -> None:
    for table in ("invoices", "subscriptions", "quotation_templates", "quotations"):
        op.drop_column(table, "line_items")
