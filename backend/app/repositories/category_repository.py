"""Category data access."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.transaction import Transaction


def get(db: Session, user_id: uuid.UUID, category_id: uuid.UUID) -> Category | None:
    return db.scalar(
        select(Category).where(Category.id == category_id, Category.user_id == user_id)
    )


def list_for_user(
    db: Session, user_id: uuid.UUID, kind: str | None = None
) -> list[Category]:
    statement = select(Category).where(Category.user_id == user_id)
    if kind:
        statement = statement.where(Category.kind == kind)
    return list(db.scalars(statement.order_by(Category.kind, Category.name)).all())


def count(db: Session, user_id: uuid.UUID) -> int:
    return db.scalar(
        select(func.count()).select_from(Category).where(Category.user_id == user_id)
    ) or 0


def name_exists(
    db: Session,
    user_id: uuid.UUID,
    name: str,
    kind: str,
    parent_id: uuid.UUID | None,
    exclude_id: uuid.UUID | None = None,
) -> bool:
    statement = select(Category.id).where(
        Category.user_id == user_id,
        Category.kind == kind,
        func.lower(Category.name) == name.lower(),
        Category.parent_id.is_(None) if parent_id is None else Category.parent_id == parent_id,
    )
    if exclude_id:
        statement = statement.where(Category.id != exclude_id)
    return db.scalar(statement) is not None


def is_in_use(db: Session, user_id: uuid.UUID, category_id: uuid.UUID) -> bool:
    """True when any transaction (including soft-deleted) references it."""
    return db.scalar(
        select(Transaction.id)
        .where(Transaction.user_id == user_id, Transaction.category_id == category_id)
        .limit(1)
    ) is not None
