"""Transaction data access with filtering, sorting and pagination."""

import uuid
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.category import Category
from app.models.transaction import Transaction

SORT_COLUMNS = {
    "transaction_date": Transaction.transaction_date,
    "amount_minor": Transaction.amount_minor,
    "created_at": Transaction.created_at,
}


def _load_options():
    return (
        joinedload(Transaction.account),
        joinedload(Transaction.destination_account),
        joinedload(Transaction.category),
        selectinload(Transaction.tags),
    )


def get(
    db: Session, user_id: uuid.UUID, transaction_id: uuid.UUID, include_deleted: bool = False
) -> Transaction | None:
    statement = (
        select(Transaction)
        .options(*_load_options())
        .where(Transaction.id == transaction_id, Transaction.user_id == user_id)
    )
    if not include_deleted:
        statement = statement.where(Transaction.deleted_at.is_(None))
    return db.scalar(statement)


def _conditions(
    user_id: uuid.UUID,
    *,
    search: str | None,
    type: str | None,
    category_id: uuid.UUID | None,
    account_id: uuid.UUID | None,
    payment_method: str | None,
    date_from: date | None,
    date_to: date | None,
    min_amount: int | None,
    max_amount: int | None,
    refund_of_id: uuid.UUID | None = None,
) -> list:
    conditions = [Transaction.user_id == user_id, Transaction.deleted_at.is_(None)]

    if type:
        conditions.append(Transaction.type == type)
    if category_id:
        conditions.append(Transaction.category_id == category_id)
    if payment_method:
        conditions.append(Transaction.payment_method == payment_method)
    if refund_of_id:
        conditions.append(Transaction.refund_of_id == refund_of_id)
    if account_id:
        conditions.append(
            or_(
                Transaction.account_id == account_id,
                Transaction.dest_account_id == account_id,
            )
        )
    if date_from:
        conditions.append(Transaction.transaction_date >= date_from)
    if date_to:
        conditions.append(Transaction.transaction_date <= date_to)
    if min_amount is not None:
        conditions.append(Transaction.amount_minor >= min_amount)
    if max_amount is not None:
        conditions.append(Transaction.amount_minor <= max_amount)
    if search:
        pattern = f"%{search.strip()}%"
        matching_categories = select(Category.id).where(
            Category.user_id == user_id, Category.name.ilike(pattern)
        )
        conditions.append(
            or_(
                Transaction.vendor.ilike(pattern),
                Transaction.description.ilike(pattern),
                Transaction.category_id.in_(matching_categories),
            )
        )
    return conditions


def list_transactions(
    db: Session,
    user_id: uuid.UUID,
    *,
    search: str | None = None,
    type: str | None = None,
    category_id: uuid.UUID | None = None,
    account_id: uuid.UUID | None = None,
    payment_method: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    min_amount: int | None = None,
    max_amount: int | None = None,
    refund_of_id: uuid.UUID | None = None,
    sort: str = "transaction_date",
    order: str = "desc",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Transaction], int]:
    conditions = _conditions(
        user_id,
        search=search,
        type=type,
        category_id=category_id,
        account_id=account_id,
        payment_method=payment_method,
        date_from=date_from,
        date_to=date_to,
        min_amount=min_amount,
        max_amount=max_amount,
        refund_of_id=refund_of_id,
    )

    total = db.scalar(select(func.count()).select_from(Transaction).where(*conditions)) or 0

    column = SORT_COLUMNS.get(sort, Transaction.transaction_date)
    ordering = column.asc() if order == "asc" else column.desc()

    statement = (
        select(Transaction)
        .options(*_load_options())
        .where(*conditions)
        .order_by(ordering, Transaction.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    return list(db.scalars(statement).unique().all()), total


def totals(db: Session, user_id: uuid.UUID, **filters) -> list[tuple[str, str, int, int]]:
    """(currency, type, sum(amount), count) grouped rows for the same filters."""
    conditions = _conditions(user_id, **filters)
    statement = (
        select(
            Transaction.currency_code,
            Transaction.type,
            func.coalesce(func.sum(Transaction.amount_minor), 0),
            func.count(Transaction.id),
        )
        .where(*conditions)
        .group_by(Transaction.currency_code, Transaction.type)
    )
    return [(row[0], row[1], int(row[2]), int(row[3])) for row in db.execute(statement).all()]


def export_transactions(
    db: Session,
    user_id: uuid.UUID,
    date_from: date,
    date_to: date,
    currency: str | None = None,
    limit: int = 10_000,
) -> list[Transaction]:
    """Every transaction in a range for CSV export (newest first)."""
    conditions = [
        Transaction.user_id == user_id,
        Transaction.deleted_at.is_(None),
        Transaction.transaction_date >= date_from,
        Transaction.transaction_date <= date_to,
    ]
    if currency:
        conditions.append(Transaction.currency_code == currency)

    statement = (
        select(Transaction)
        .options(*_load_options())
        .where(*conditions)
        .order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(statement).unique().all())
