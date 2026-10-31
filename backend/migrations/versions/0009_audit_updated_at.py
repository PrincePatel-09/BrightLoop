"""add updated timestamp to audit events

Revision ID: 0009_audit_updated_at
Revises: 0008_audit_events
Create Date: 2026-10-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_audit_updated_at"
down_revision: Union[str, Sequence[str], None] = "0008_audit_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("audit_events", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))


def downgrade() -> None:
    op.drop_column("audit_events", "updated_at")
