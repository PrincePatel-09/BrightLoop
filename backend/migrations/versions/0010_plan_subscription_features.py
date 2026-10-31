"""add plan and subscription feature snapshots

Revision ID: 0010_plan_subscription_features
Revises: 0009_audit_updated_at
Create Date: 2026-10-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010_plan_subscription_features"
down_revision: Union[str, Sequence[str], None] = "0009_audit_updated_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("plans", sa.Column("features", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("subscriptions", sa.Column("features", sa.JSON(), nullable=False, server_default="[]"))


def downgrade() -> None:
    op.drop_column("subscriptions", "features")
    op.drop_column("plans", "features")
