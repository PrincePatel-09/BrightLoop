"""rename seeded company branding to Brightloop

Revision ID: 0019_brightloop_branding
Revises: 0018_credit_notes_refunds
Create Date: 2026-10-31
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0019_brightloop_branding"
down_revision: Union[str, Sequence[str], None] = "0018_credit_notes_refunds"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE companies SET name = 'Brightloop Software', legal_name = 'Brightloop Software', slug = 'brightloop-demo' WHERE slug = 'subnexa-demo'")
    op.execute("UPDATE app_settings SET value = 'Brightloop Software' WHERE key = 'company_name'")


def downgrade() -> None:
    op.execute("UPDATE companies SET name = 'SubNexa Demo Company', legal_name = 'SubNexa Demo Company', slug = 'subnexa-demo' WHERE slug = 'brightloop-demo'")
