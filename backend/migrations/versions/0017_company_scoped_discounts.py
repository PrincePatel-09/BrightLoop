"""scope discount codes to company workspaces

Revision ID: 0017_company_scoped_discounts
Revises: 0016_company_gst_invoice_sequences
Create Date: 2026-10-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0017_company_scoped_discounts"
down_revision: Union[str, Sequence[str], None] = "0016_company_gst_invoice_sequences"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    company_id = bind.execute(sa.text("SELECT id FROM companies WHERE slug = 'subnexa-demo'")).scalar()
    if company_id is None:
        raise RuntimeError("Default company is required before scoping existing discount codes")
    op.add_column("discounts", sa.Column("company_id", sa.Integer(), nullable=True))
    op.execute(sa.text("UPDATE discounts SET company_id = :company_id WHERE company_id IS NULL").bindparams(company_id=company_id))
    with op.batch_alter_table("discounts") as batch:
        batch.alter_column("company_id", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key("fk_discounts_company_id", "companies", ["company_id"], ["id"], ondelete="RESTRICT")
    op.drop_index("ix_discounts_code", table_name="discounts")
    op.create_index("ix_discounts_company_id", "discounts", ["company_id"])
    op.create_index("uq_discounts_company_code", "discounts", ["company_id", "code"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_discounts_company_code", table_name="discounts")
    op.drop_index("ix_discounts_company_id", table_name="discounts")
    with op.batch_alter_table("discounts") as batch:
        batch.drop_constraint("fk_discounts_company_id", type_="foreignkey")
        batch.drop_column("company_id")
    op.create_index("ix_discounts_code", "discounts", ["code"], unique=True)
