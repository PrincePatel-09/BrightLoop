"""add customer subscription change requests

Revision ID: 0014_subscription_change_requests
Revises: 0013_company_data_scope
Create Date: 2026-10-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014_subscription_change_requests"
down_revision: Union[str, Sequence[str], None] = "0013_company_data_scope"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "subscription_change_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("subscription_id", sa.Integer(), sa.ForeignKey("subscriptions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("requested_plan_id", sa.Integer(), sa.ForeignKey("plans.id", ondelete="RESTRICT")),
        sa.Column("request_type", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("notes", sa.Text()),
        sa.Column("decided_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("request_type IN ('pause', 'resume', 'cancel', 'upgrade', 'downgrade')", name="ck_subscription_change_request_type"),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="ck_subscription_change_request_status"),
    )
    op.create_index("ix_subscription_change_requests_company_id", "subscription_change_requests", ["company_id"])
    op.create_index("ix_subscription_change_requests_customer_id", "subscription_change_requests", ["customer_id"])
    op.create_index("ix_subscription_change_requests_subscription_id", "subscription_change_requests", ["subscription_id"])
    op.create_index("ix_subscription_change_requests_status", "subscription_change_requests", ["status"])


def downgrade() -> None:
    op.drop_index("ix_subscription_change_requests_status", table_name="subscription_change_requests")
    op.drop_index("ix_subscription_change_requests_subscription_id", table_name="subscription_change_requests")
    op.drop_index("ix_subscription_change_requests_customer_id", table_name="subscription_change_requests")
    op.drop_index("ix_subscription_change_requests_company_id", table_name="subscription_change_requests")
    op.drop_table("subscription_change_requests")
