"""Idempotent daily job: generate bills, flag overdue, raise notifications."""

import uuid
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.budget import Budget
from app.models.currency import Currency
from app.models.enums import BillStatus
from app.models.notification import Notification
from app.models.recurring import Bill, RecurringTransaction
from app.repositories import bill_repository, profile_repository
from app.services import budget_service, recurring_service

UPCOMING_HORIZON_DAYS = 7


def _decimal_string(amount_minor: int, decimal_places: int) -> str:
    if decimal_places <= 0:
        return str(amount_minor)
    whole, fraction = divmod(amount_minor, 10**decimal_places)
    return f"{whole}.{fraction:0{decimal_places}d}"


def _generate_bills(
    db: Session, recurring: RecurringTransaction, today: date, counts: dict
) -> None:
    horizon = today + timedelta(days=max(recurring.reminder_days, UPCOMING_HORIZON_DAYS))
    guard = 0

    while recurring.is_active and recurring.next_occurrence <= horizon and guard < 100:
        occurrence = recurring.next_occurrence
        if recurring.end_date and occurrence > recurring.end_date:
            recurring.is_active = False
            break

        bill = Bill(
            user_id=recurring.user_id,
            recurring_id=recurring.id,
            due_date=occurrence,
            amount_minor=recurring.amount_minor,
            currency_code=recurring.currency_code,
            status=BillStatus.PENDING,
        )
        try:
            with db.begin_nested():
                db.add(bill)
                db.flush()
            counts["bills_created"] += 1
        except IntegrityError:
            # The unique (recurring_id, due_date) makes re-runs harmless.
            pass

        recurring.next_occurrence = recurring_service.advance(
            occurrence, recurring.frequency, recurring.interval_count
        )
        guard += 1

        if recurring.end_date and recurring.next_occurrence > recurring.end_date:
            recurring.is_active = False


def _notify_due_bills(
    db: Session, user_id: uuid.UUID, today: date, counts: dict, preferences
) -> None:
    if preferences is not None and not preferences.notify_upcoming_bills:
        return

    horizon = today + timedelta(days=30)
    bills = db.scalars(
        select(Bill)
        .options(joinedload(Bill.recurring))
        .where(
            Bill.user_id == user_id,
            Bill.status.in_((BillStatus.PENDING, BillStatus.OVERDUE)),
            Bill.due_date >= today - timedelta(days=14),
            Bill.due_date <= horizon,
        )
    ).all()

    for bill in bills:
        recurring = bill.recurring
        if bill.due_date > today + timedelta(days=recurring.reminder_days):
            continue

        dedupe_key = f"bill:{bill.id}"
        if bill_repository.notification_exists(
            db, user_id, "bill_due", "dedupe_key", dedupe_key
        ):
            continue

        label = recurring.vendor or (
            recurring.category.name if recurring.category else "Upcoming bill"
        )
        db.add(
            Notification(
                user_id=user_id,
                type="bill_due",
                title=f"Bill due: {label}",
                body=(
                    f"{bill.amount_minor} {bill.currency_code} is due on "
                    f"{bill.due_date.isoformat()}. Review it on the Recurring page."
                ),
                payload={
                    "dedupe_key": dedupe_key,
                    "bill_id": str(bill.id),
                    "due_date": bill.due_date.isoformat(),
                    "amount_minor": bill.amount_minor,
                    "currency_code": bill.currency_code,
                },
            )
        )
        counts["notifications_created"] += 1


def _notify_budgets(
    db: Session,
    user_id: uuid.UUID,
    timezone: str,
    counts: dict,
    decimal_places: dict,
    preferences,
) -> None:
    if preferences is not None and not preferences.notify_budget_thresholds:
        return

    for budget in budget_service.list_budgets(db, user_id, timezone):
        if budget["state"] not in {"critical", "exceeded"}:
            continue

        dedupe_key = f"budget:{budget['id']}:{budget['period_start']}"
        if bill_repository.notification_exists(
            db, user_id, "budget_threshold", "dedupe_key", dedupe_key
        ):
            continue

        places = decimal_places.get(budget["currency_code"], 2)
        db.add(
            Notification(
                user_id=user_id,
                type="budget_threshold",
                title=f"{budget['name']} is at {budget['percent_used']}%",
                body=(
                    f"Spent {_decimal_string(budget['spent_minor'], places)} of "
                    f"{_decimal_string(budget['amount_minor'], places)} "
                    f"{budget['currency_code']} this period."
                ),
                payload={
                    "dedupe_key": dedupe_key,
                    "budget_id": budget["id"],
                    "period_start": budget["period_start"],
                    "percent_used": budget["percent_used"],
                    "state": budget["state"],
                },
            )
        )
        counts["notifications_created"] += 1


def run(db: Session, user_id: uuid.UUID | None = None) -> dict:
    counts = {
        "bills_created": 0,
        "bills_overdue": 0,
        "notifications_created": 0,
        "users_processed": 0,
    }

    if user_id is not None:
        # On-demand run from the app: only the signed-in user's data.
        user_ids = {user_id}
    else:
        user_ids = set(
            db.scalars(
                select(RecurringTransaction.user_id).where(
                    RecurringTransaction.is_active.is_(True)
                )
            ).all()
        ) | set(
            db.scalars(select(Budget.user_id).where(Budget.is_active.is_(True))).all()
        )

    decimal_places = {
        code: places for code, places in db.execute(select(Currency.code, Currency.decimal_places))
    }

    for user_id in user_ids:
        preferences = profile_repository.get_preferences(db, user_id)
        timezone = preferences.timezone if preferences else "Africa/Lagos"
        today = datetime.now(ZoneInfo(timezone)).date()

        recurring_items = db.scalars(
            select(RecurringTransaction).where(
                RecurringTransaction.user_id == user_id,
                RecurringTransaction.is_active.is_(True),
            )
        ).all()
        for recurring in recurring_items:
            _generate_bills(db, recurring, today, counts)

        db.flush()

        result = db.execute(
            update(Bill)
            .where(
                Bill.user_id == user_id,
                Bill.status == BillStatus.PENDING,
                Bill.due_date < today,
            )
            .values(status=BillStatus.OVERDUE)
        )
        counts["bills_overdue"] += result.rowcount or 0

        _notify_due_bills(db, user_id, today, counts, preferences)
        _notify_budgets(db, user_id, timezone, counts, decimal_places, preferences)

        db.commit()
        counts["users_processed"] += 1

    return counts
