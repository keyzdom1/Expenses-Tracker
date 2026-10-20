"""Schema-level guarantees: RLS, seed data and required constraints."""

import uuid
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.models.account import Account
from app.models.enums import AccountType, TransactionType
from app.models.profile import Profile
from app.models.transaction import Transaction

RLS_TABLES = [
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


def test_every_table_has_row_level_security_enabled(db):
    rows = db.execute(
        text(
            "SELECT relname FROM pg_class "
            "WHERE relname = ANY(:tables) AND relrowsecurity = true"
        ),
        {"tables": RLS_TABLES},
    ).scalars()

    assert set(rows) == set(RLS_TABLES)


def test_currencies_are_seeded_with_correct_decimals(db):
    rows = dict(db.execute(text("SELECT code, decimal_places FROM currencies")).all())

    assert rows["NGN"] == 2
    assert rows["JPY"] == 0
    assert len(rows) == 10


def _make_account(db) -> Account:
    profile = Profile(id=uuid.uuid4(), email="schema@example.com")
    db.add(profile)
    db.flush()
    account = Account(
        user_id=profile.id,
        name="Cash",
        type=AccountType.CASH,
        currency_code="NGN",
    )
    db.add(account)
    db.flush()
    return account


def test_transaction_amount_must_be_positive(db):
    account = _make_account(db)

    transaction = Transaction(
        user_id=account.user_id,
        account_id=account.id,
        type=TransactionType.EXPENSE,
        amount_minor=0,
        currency_code="NGN",
        transaction_date=date.today(),
    )
    db.add(transaction)

    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_transfer_requires_a_different_destination_account(db):
    account = _make_account(db)

    transaction = Transaction(
        user_id=account.user_id,
        account_id=account.id,
        type=TransactionType.TRANSFER,
        amount_minor=5000,
        currency_code="NGN",
        transaction_date=date.today(),
    )
    db.add(transaction)

    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_non_transfer_cannot_have_a_destination_account(db):
    source = _make_account(db)
    destination = Account(
        user_id=source.user_id,
        name="Bank",
        type=AccountType.BANK,
        currency_code="NGN",
    )
    db.add(destination)
    db.flush()

    transaction = Transaction(
        user_id=source.user_id,
        account_id=source.id,
        dest_account_id=destination.id,
        type=TransactionType.EXPENSE,
        amount_minor=5000,
        currency_code="NGN",
        transaction_date=date.today(),
    )
    db.add(transaction)

    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()
