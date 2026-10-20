"""Aggregate reporting queries.

Every figure on the dashboard comes from these queries. Transfers are excluded
from income and spending; refunds reduce spending in their category.
"""

import uuid
from datetime import date

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.transaction import Transaction

REPORT_TYPES = ("income", "expense", "refund")


def type_totals(
    db: Session, user_id: uuid.UUID, currency: str, date_from: date, date_to: date
) -> list[tuple[str, int, int]]:
    statement = (
        select(
            Transaction.type,
            func.coalesce(func.sum(Transaction.amount_minor), 0),
            func.count(Transaction.id),
        )
        .where(
            Transaction.user_id == user_id,
            Transaction.currency_code == currency,
            Transaction.deleted_at.is_(None),
            Transaction.transaction_date >= date_from,
            Transaction.transaction_date <= date_to,
            Transaction.type.in_(REPORT_TYPES),
        )
        .group_by(Transaction.type)
    )
    return [(row[0], int(row[1]), int(row[2])) for row in db.execute(statement).all()]


def category_spending(
    db: Session, user_id: uuid.UUID, currency: str, date_from: date, date_to: date
) -> list[tuple[uuid.UUID | None, str | None, str, int]]:
    """(category_id, category_name, type, sum) for expenses and refunds."""
    statement = (
        select(
            Transaction.category_id,
            Category.name,
            Transaction.type,
            func.coalesce(func.sum(Transaction.amount_minor), 0),
        )
        .join(Category, Transaction.category_id == Category.id, isouter=True)
        .where(
            Transaction.user_id == user_id,
            Transaction.currency_code == currency,
            Transaction.deleted_at.is_(None),
            Transaction.transaction_date >= date_from,
            Transaction.transaction_date <= date_to,
            Transaction.type.in_(("expense", "refund")),
        )
        .group_by(Transaction.category_id, Category.name, Transaction.type)
    )
    return [
        (row[0], row[1], row[2], int(row[3])) for row in db.execute(statement).all()
    ]


def monthly_flow(
    db: Session, user_id: uuid.UUID, currency: str, date_from: date, date_to: date
) -> list[tuple[date, str, int]]:
    month = func.date_trunc("month", Transaction.transaction_date)
    statement = (
        select(
            month.label("month"),
            Transaction.type,
            func.coalesce(func.sum(Transaction.amount_minor), 0),
        )
        .where(
            Transaction.user_id == user_id,
            Transaction.currency_code == currency,
            Transaction.deleted_at.is_(None),
            Transaction.transaction_date >= date_from,
            Transaction.transaction_date <= date_to,
            Transaction.type.in_(REPORT_TYPES),
        )
        .group_by(month, Transaction.type)
        .order_by(month)
    )
    return [
        (row[0].date() if hasattr(row[0], "date") else row[0], row[1], int(row[2]))
        for row in db.execute(statement).all()
    ]


def budget_spent(
    db: Session,
    user_id: uuid.UUID,
    currency: str,
    date_from: date,
    date_to: date,
    category_id: uuid.UUID | None = None,
) -> int:
    """Net spending (expenses minus refunds) in a window."""
    conditions = [
        Transaction.user_id == user_id,
        Transaction.currency_code == currency,
        Transaction.deleted_at.is_(None),
        Transaction.transaction_date >= date_from,
        Transaction.transaction_date <= date_to,
        Transaction.type.in_(("expense", "refund")),
    ]
    if category_id is not None:
        conditions.append(Transaction.category_id == category_id)

    signed = func.coalesce(
        func.sum(
            case(
                (Transaction.type == "expense", Transaction.amount_minor),
                else_=-Transaction.amount_minor,
            )
        ),
        0,
    )
    return int(db.scalar(select(signed).where(*conditions)) or 0)
