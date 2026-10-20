"""Bill and notification data access."""

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.notification import Notification
from app.models.recurring import Bill, RecurringTransaction


def _bill_options():
    return (
        joinedload(Bill.recurring).joinedload(RecurringTransaction.account),
        joinedload(Bill.recurring).joinedload(RecurringTransaction.destination_account),
        joinedload(Bill.recurring).joinedload(RecurringTransaction.category),
    )


def get_bill(db: Session, user_id: uuid.UUID, bill_id: uuid.UUID) -> Bill | None:
    return db.scalar(
        select(Bill)
        .options(*_bill_options())
        .where(Bill.id == bill_id, Bill.user_id == user_id)
    )


def list_bills(
    db: Session,
    user_id: uuid.UUID,
    status: str | None = None,
    due_from: date | None = None,
    due_to: date | None = None,
) -> list[Bill]:
    statement = (
        select(Bill)
        .options(*_bill_options())
        .where(Bill.user_id == user_id)
    )
    if status:
        statement = statement.where(Bill.status == status)
    if due_from:
        statement = statement.where(Bill.due_date >= due_from)
    if due_to:
        statement = statement.where(Bill.due_date <= due_to)
    return list(db.scalars(statement.order_by(Bill.due_date.asc())).all())


def list_notifications(
    db: Session, user_id: uuid.UUID, unread_only: bool = False, limit: int = 50
) -> list[Notification]:
    statement = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        statement = statement.where(Notification.read_at.is_(None))
    return list(
        db.scalars(statement.order_by(Notification.created_at.desc()).limit(limit)).all()
    )


def unread_count(db: Session, user_id: uuid.UUID) -> int:
    return db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user_id, Notification.read_at.is_(None))
    ) or 0


def get_notification(
    db: Session, user_id: uuid.UUID, notification_id: uuid.UUID
) -> Notification | None:
    return db.scalar(
        select(Notification).where(
            Notification.id == notification_id, Notification.user_id == user_id
        )
    )


def notification_exists(
    db: Session, user_id: uuid.UUID, notification_type: str, key: str, value: str
) -> bool:
    return db.scalar(
        select(Notification.id)
        .where(
            Notification.user_id == user_id,
            Notification.type == notification_type,
            Notification.payload[key].astext == value,
        )
        .limit(1)
    ) is not None
