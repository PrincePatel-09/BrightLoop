"""add company-scoped reusable quotation templates

Revision ID: 0020_quotation_templates
Revises: 0019_brightloop_branding
Create Date: 2026-10-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0020_quotation_templates"
down_revision: Union[str, Sequence[str], None] = "0019_brightloop_branding"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "quotation_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("valid_days", sa.Integer(), nullable=False, server_default="14"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("discount_code", sa.String(length=40), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_quotation_templates_quantity_positive"),
        sa.CheckConstraint("valid_days > 0", name="ck_quotation_templates_valid_days_positive"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "name", name="uq_quotation_templates_company_name"),
    )
    op.create_index("ix_quotation_templates_company_id", "quotation_templates", ["company_id"])
    op.create_index("ix_quotation_templates_plan_id", "quotation_templates", ["plan_id"])


def downgrade() -> None:
    op.drop_index("ix_quotation_templates_plan_id", table_name="quotation_templates")
    op.drop_index("ix_quotation_templates_company_id", table_name="quotation_templates")
    op.drop_table("quotation_templates")
