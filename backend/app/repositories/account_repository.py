"""Account data access and derived balances."""

import uuid

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.transaction import Transaction


def get(db: Session, user_id: uuid.UUID, account_id: uuid.UUID) -> Account | None:
    return db.scalar(
        select(Account).where(Account.id == account_id, Account.user_id == user_id)
    )


def list_for_user(db: Session, user_id: uuid.UUID, include_archived: bool = False) -> list[Account]:
    statement = select(Account).where(Account.user_id == user_id)
    if not include_archived:
        statement = statement.where(Account.is_active.is_(True))
    return list(db.scalars(statement.order_by(Account.name)).all())


def balances(db: Session, user_id: uuid.UUID) -> dict[uuid.UUID, int]:
    """Derived balance for every account, in one query.

    balance = opening
              + income + refunds - expenses (as the source account)
              + transfers in - transfers out
    Soft-deleted rows never participate.
    """
    t = Transaction
    signed = case(
        (
            and_(t.type.in_(["income", "refund"]), t.account_id == Account.id),
            t.amount_minor,
        ),
        (and_(t.type == "expense", t.account_id == Account.id), -t.amount_minor),
        (and_(t.type == "transfer", t.account_id == Account.id), -t.amount_minor),
        (and_(t.type == "transfer", t.dest_account_id == Account.id), t.amount_minor),
        else_=0,
    )

    statement = (
        select(Account.id, (Account.opening_balance_minor + func.coalesce(func.sum(signed), 0)).label("balance"))
        .outerjoin(
            t,
            and_(
                t.deleted_at.is_(None),
                (t.account_id == Account.id) | (t.dest_account_id == Account.id),
            ),
        )
        .where(Account.user_id == user_id)
        .group_by(Account.id, Account.opening_balance_minor)
    )

    return {row.id: int(row.balance) for row in db.execute(statement).all()}


def has_transactions(db: Session, user_id: uuid.UUID, account_id: uuid.UUID) -> bool:
    return db.scalar(
        select(Transaction.id)
        .where(
            Transaction.user_id == user_id,
            (Transaction.account_id == account_id) | (Transaction.dest_account_id == account_id),
        )
        .limit(1)
    ) is not None


def name_exists(db: Session, user_id: uuid.UUID, name: str, exclude_id: uuid.UUID | None = None) -> bool:
    statement = select(Account.id).where(
        Account.user_id == user_id, func.lower(Account.name) == name.lower()
    )
    if exclude_id:
        statement = statement.where(Account.id != exclude_id)
    return db.scalar(statement) is not None
