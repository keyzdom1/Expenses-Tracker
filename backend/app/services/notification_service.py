"""In-app notifications."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.repositories import bill_repository
from app.schemas.notification import NotificationOut


def _serialize(notification) -> dict:
    return NotificationOut.model_validate(notification).model_dump(mode="json")


def list_notifications(
    db: Session, user_id: uuid.UUID, unread_only: bool = False, limit: int = 50
) -> tuple[list[dict], int]:
    items = bill_repository.list_notifications(db, user_id, unread_only, limit)
    return [_serialize(item) for item in items], bill_repository.unread_count(db, user_id)


def mark_read(db: Session, user_id: uuid.UUID, notification_id: uuid.UUID) -> dict:
    notification = bill_repository.get_notification(db, user_id, notification_id)
    if notification is None:
        raise APIError(404, "not_found", "Notification not found.")

    if notification.read_at is None:
        notification.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(notification)

    return _serialize(notification)


def mark_all_read(db: Session, user_id: uuid.UUID) -> int:
    items = bill_repository.list_notifications(db, user_id, unread_only=True, limit=500)
    now = datetime.now(timezone.utc)
    for item in items:
        item.read_at = now
    db.commit()
    return len(items)
