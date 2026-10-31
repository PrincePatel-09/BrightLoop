"""add company ownership to customer and billing records

Revision ID: 0013_company_data_scope
Revises: 0012_product_variants
Create Date: 2026-10-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013_company_data_scope"
down_revision: Union[str, Sequence[str], None] = "0012_product_variants"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    companies = sa.table(
        "companies",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("legal_name", sa.String),
        sa.column("slug", sa.String),
        sa.column("is_active", sa.Boolean),
    )
    default_id = bind.execute(sa.select(companies.c.id).where(companies.c.slug == "subnexa-demo")).scalar()
    if default_id is None:
        bind.execute(companies.insert().values(
            name="SubNexa Demo Company",
            legal_name="SubNexa Demo Company",
            slug="subnexa-demo",
            is_active=True,
        ))
        default_id = bind.execute(sa.select(companies.c.id).where(companies.c.slug == "subnexa-demo")).scalar_one()

    op.add_column("customers", sa.Column("company_id", sa.Integer(), nullable=True))
    op.add_column("products", sa.Column("company_id", sa.Integer(), nullable=True))
    op.add_column("quotations", sa.Column("company_id", sa.Integer(), nullable=True))
    op.add_column("subscriptions", sa.Column("company_id", sa.Integer(), nullable=True))
    op.add_column("invoices", sa.Column("company_id", sa.Integer(), nullable=True))

    bind.execute(sa.text("UPDATE users SET company_id = :company_id WHERE role = 'customer' AND company_id IS NULL"), {"company_id": default_id})
    bind.execute(sa.text("UPDATE customers SET company_id = COALESCE((SELECT company_id FROM users WHERE users.id = customers.user_id), :company_id)"), {"company_id": default_id})
    bind.execute(sa.text("UPDATE products SET company_id = :company_id WHERE company_id IS NULL"), {"company_id": default_id})
    bind.execute(sa.text("UPDATE quotations SET company_id = (SELECT company_id FROM customers WHERE customers.id = quotations.customer_id)"))
    bind.execute(sa.text("UPDATE subscriptions SET company_id = (SELECT company_id FROM customers WHERE customers.id = subscriptions.customer_id)"))
    bind.execute(sa.text("UPDATE invoices SET company_id = (SELECT company_id FROM subscriptions WHERE subscriptions.id = invoices.subscription_id)"))

    for table in ("customers", "products", "quotations", "subscriptions", "invoices"):
        with op.batch_alter_table(table) as batch:
            batch.alter_column("company_id", existing_type=sa.Integer(), nullable=False)
            batch.create_foreign_key(f"fk_{table}_company_id", "companies", ["company_id"], ["id"], ondelete="RESTRICT")
            batch.create_index(f"ix_{table}_company_id", ["company_id"])


def downgrade() -> None:
    for table in ("invoices", "subscriptions", "quotations", "products", "customers"):
        with op.batch_alter_table(table) as batch:
            batch.drop_index(f"ix_{table}_company_id")
            batch.drop_constraint(f"fk_{table}_company_id", type_="foreignkey")
            batch.drop_column("company_id")
