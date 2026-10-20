"""Recurring template business rules and date maths."""

import calendar
import uuid
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.models.enums import RecurrenceFrequency, TransactionType
from app.models.recurring import RecurringTransaction
from app.repositories import recurring_repository
from app.schemas.recurring import RecurringCreate, RecurringOut, RecurringUpdate
from app.services import transaction_service


def advance(value: date, frequency: RecurrenceFrequency, interval: int) -> date:
    """Move a date forward by one recurrence interval, clamping month ends."""
    if frequency == RecurrenceFrequency.DAILY:
        return value + timedelta(days=interval)
    if frequency == RecurrenceFrequency.WEEKLY:
        return value + timedelta(weeks=interval)
    if frequency == RecurrenceFrequency.YEARLY:
        year = value.year + interval
        day = min(value.day, calendar.monthrange(year, value.month)[1])
        return value.replace(year=year, day=day)

    month_index = value.year * 12 + (value.month - 1) + interval
    year, month = divmod(month_index, 12)
    month += 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _serialize(recurring: RecurringTransaction) -> dict:
    return RecurringOut.model_validate(recurring).model_dump(mode="json")


def get_recurring(
    db: Session, user_id: uuid.UUID, recurring_id: uuid.UUID
) -> RecurringTransaction:
    recurring = recurring_repository.get(db, user_id, recurring_id)
    if recurring is None:
        raise APIError(404, "not_found", "Recurring transaction not found.")
    return recurring


def list_recurring(
    db: Session, user_id: uuid.UUID, include_inactive: bool = False
) -> list[dict]:
    return [
        _serialize(item)
        for item in recurring_repository.list_for_user(db, user_id, include_inactive)
    ]


def _resolved(db: Session, user_id: uuid.UUID, values: dict) -> dict:
    merged = {
        **values,
        "currency_code": None,
        "refund_of_id": None,
        "tag_ids": [],
    }
    return transaction_service._resolve_all(db, user_id, merged)


def create_recurring(
    db: Session, user_id: uuid.UUID, data: RecurringCreate
) -> dict:
    resolved = _resolved(db, user_id, data.model_dump(mode="python"))

    recurring = RecurringTransaction(
        user_id=user_id,
        account_id=resolved["account"].id,
        dest_account_id=resolved["destination"].id if resolved["destination"] else None,
        category_id=resolved["category"].id if resolved["category"] else None,
        type=data.type,
        amount_minor=data.amount_minor,
        currency_code=resolved["currency_code"],
        payment_method=data.payment_method,
        vendor=data.vendor,
        description=data.description,
        frequency=data.frequency,
        interval_count=data.interval_count,
        start_date=data.start_date,
        end_date=data.end_date,
        next_occurrence=data.start_date,
        reminder_days=data.reminder_days,
    )
    db.add(recurring)
    db.commit()
    db.refresh(recurring)
    return _serialize(recurring)


def update_recurring(
    db: Session, user_id: uuid.UUID, recurring_id: uuid.UUID, data: RecurringUpdate
) -> dict:
    recurring = get_recurring(db, user_id, recurring_id)
    changes = data.model_dump(exclude_unset=True)

    # Required columns: an explicit null means "leave unchanged".
    for required in ("type", "amount_minor", "frequency", "interval_count", "start_date"):
        if required in changes and changes[required] is None:
            changes.pop(required)

    merged = {
        "type": recurring.type,
        "account_id": recurring.account_id,
        "dest_account_id": recurring.dest_account_id,
        "category_id": recurring.category_id,
        "currency_code": None,
        "refund_of_id": None,
        "tag_ids": [],
    }
    for field in ("type", "account_id", "dest_account_id", "category_id"):
        if field in changes:
            merged[field] = changes[field]

    if "account_id" in changes and changes["account_id"] is None:
        raise APIError(422, "account_required", "Choose an account.")

    if merged["type"] != TransactionType.TRANSFER and "dest_account_id" not in changes:
        merged["dest_account_id"] = None
    if merged["type"] == TransactionType.TRANSFER and "category_id" not in changes:
        merged["category_id"] = None

    start_date = changes.get("start_date", recurring.start_date)
    end_date = changes.get("end_date", recurring.end_date)
    if end_date and end_date < start_date:
        raise APIError(422, "invalid_date_range", "The end date must be on or after the start date.")

    resolved = _resolved(db, user_id, merged)

    recurring.type = merged["type"]
    recurring.account_id = resolved["account"].id
    recurring.dest_account_id = (
        resolved["destination"].id if resolved["destination"] else None
    )
    recurring.category_id = resolved["category"].id if resolved["category"] else None
    recurring.currency_code = resolved["currency_code"]

    for field in (
        "amount_minor",
        "payment_method",
        "vendor",
        "description",
        "frequency",
        "interval_count",
        "start_date",
        "end_date",
        "reminder_days",
        "is_active",
    ):
        if field in changes:
            setattr(recurring, field, changes[field])

    if "start_date" in changes and changes["start_date"] is not None:
        recurring.next_occurrence = changes["start_date"]

    db.commit()
    db.refresh(recurring)
    return _serialize(recurring)


def deactivate_recurring(
    db: Session, user_id: uuid.UUID, recurring_id: uuid.UUID
) -> dict:
    recurring = get_recurring(db, user_id, recurring_id)
    recurring.is_active = False
    db.commit()
    db.refresh(recurring)
    return _serialize(recurring)
