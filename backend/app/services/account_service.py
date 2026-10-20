"""Account business rules and balance calculation."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import APIError
from app.models.account import Account
from app.models.enums import AccountType
from app.repositories import account_repository, profile_repository


def list_accounts(db: Session, user_id: uuid.UUID, include_archived: bool = False):
    accounts = account_repository.list_for_user(db, user_id, include_archived)
    balances = account_repository.balances(db, user_id)
    return [(account, balances.get(account.id, account.opening_balance_minor)) for account in accounts]


def get_account(db: Session, user_id: uuid.UUID, account_id: uuid.UUID) -> Account:
    account = account_repository.get(db, user_id, account_id)
    if account is None:
        raise APIError(404, "not_found", "Account not found.")
    return account


def get_balance(db: Session, user_id: uuid.UUID, account_id: uuid.UUID) -> int:
    return account_repository.balances(db, user_id).get(account_id, 0)


def create_account(db: Session, user_id: uuid.UUID, data: dict) -> Account:
    settings = get_settings()
    preferences = profile_repository.get_preferences(db, user_id)
    currency = data.get("currency_code") or (
        preferences.currency_code if preferences else settings.default_currency
    )

    if not profile_repository.currency_exists(db, currency):
        raise APIError(422, "unknown_currency", f"Currency {currency} is not supported.")

    if account_repository.name_exists(db, user_id, data["name"]):
        raise APIError(409, "duplicate_account", "You already have an account with that name.")

    account = Account(
        user_id=user_id,
        name=data["name"],
        type=data["type"],
        currency_code=currency,
        opening_balance_minor=data.get("opening_balance_minor", 0),
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def update_account(db: Session, user_id: uuid.UUID, account_id: uuid.UUID, changes: dict) -> Account:
    account = get_account(db, user_id, account_id)

    if account.archived_at is not None:
        raise APIError(409, "account_archived", "Archived accounts cannot be edited.")

    if "name" in changes and changes["name"]:
        if account_repository.name_exists(db, user_id, changes["name"], exclude_id=account.id):
            raise APIError(409, "duplicate_account", "You already have an account with that name.")

    for field in ("name", "type", "opening_balance_minor"):
        if field in changes:
            setattr(account, field, changes[field])

    db.commit()
    db.refresh(account)
    return account


def archive_account(db: Session, user_id: uuid.UUID, account_id: uuid.UUID) -> Account:
    """Accounts are archived rather than deleted, preserving transaction history."""
    account = get_account(db, user_id, account_id)

    if account.archived_at is None:
        account.is_active = False
        account.archived_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(account)

    return account
