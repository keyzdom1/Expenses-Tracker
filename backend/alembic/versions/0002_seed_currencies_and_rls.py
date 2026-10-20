"""Seed currencies and enable deny-by-default row level security.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-19

RLS is enabled on every table with **no policies**, so the anon/authenticated
roles used by Supabase clients cannot read or write anything directly. The API
connects with a privileged role and still filters every query by user_id.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CURRENCIES = [
    ("NGN", "Nigerian Naira", 2),
    ("USD", "US Dollar", 2),
    ("EUR", "Euro", 2),
    ("GBP", "Pound Sterling", 2),
    ("CAD", "Canadian Dollar", 2),
    ("AUD", "Australian Dollar", 2),
    ("GHS", "Ghanaian Cedi", 2),
    ("KES", "Kenyan Shilling", 2),
    ("ZAR", "South African Rand", 2),
    ("JPY", "Japanese Yen", 0),
]

TABLES = [
    "accounts",
    "audit_logs",
    "bills",
    "budgets",
    "categories",
    "currencies",
    "idempotency_keys",
    "notifications",
    "profiles",
    "receipts",
    "recurring_transactions",
    "savings_goals",
    "tags",
    "transaction_tags",
    "transactions",
    "user_preferences",
]


def upgrade() -> None:
    currencies = sa.table(
        "currencies",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("decimal_places", sa.SmallInteger),
    )
    op.bulk_insert(
        currencies,
        [
            {"code": code, "name": name, "decimal_places": decimals}
            for code, name, decimals in CURRENCIES
        ],
    )

    for table in TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    for table in TABLES:
        op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')

    op.execute(
        "DELETE FROM currencies WHERE code IN "
        "('NGN', 'USD', 'EUR', 'GBP', 'CAD', 'AUD', 'GHS', 'KES', 'ZAR', 'JPY')"
    )
