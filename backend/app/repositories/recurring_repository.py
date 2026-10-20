"""Recurring template data access."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.recurring import RecurringTransaction


def _options():
    return (
        joinedload(RecurringTransaction.account),
        joinedload(RecurringTransaction.destination_account),
        joinedload(RecurringTransaction.category),
    )


def get(db: Session, user_id: uuid.UUID, recurring_id: uuid.UUID) -> RecurringTransaction | None:
    return db.scalar(
        select(RecurringTransaction)
        .options(*_options())
        .where(
            RecurringTransaction.id == recurring_id,
            RecurringTransaction.user_id == user_id,
        )
    )


def list_for_user(
    db: Session, user_id: uuid.UUID, include_inactive: bool = False
) -> list[RecurringTransaction]:
    statement = (
        select(RecurringTransaction)
        .options(*_options())
        .where(RecurringTransaction.user_id == user_id)
    )
    if not include_inactive:
        statement = statement.where(RecurringTransaction.is_active.is_(True))
    return list(db.scalars(statement.order_by(RecurringTransaction.created_at.desc())).all())
