"""Authoritative dashboard reporting."""

import calendar
import csv
import io
import uuid
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import APIError
from app.models.currency import Currency
from app.repositories import (
    account_repository,
    profile_repository,
    report_repository,
    transaction_repository,
)

MAX_RANGE_DAYS = 731  # two years


def _month_start(value: date) -> date:
    return value.replace(day=1)


def _month_end(value: date) -> date:
    return value.replace(day=calendar.monthrange(value.year, value.month)[1])


def _add_months(value: date, months: int) -> date:
    month_index = value.year * 12 + (value.month - 1) + months
    year, month = divmod(month_index, 12)
    return date(year, month + 1, 1)


def _period_label(date_from: date, date_to: date) -> str:
    if date_from == _month_start(date_from) and date_to == _month_end(date_to):
        if date_from.year == date_to.year and date_from.month == date_to.month:
            return date_from.strftime("%B %Y")
    return f"{date_from:%d %b %Y} - {date_to:%d %b %Y}"


def resolve_period(
    timezone: str, date_from: date | None, date_to: date | None
) -> tuple[date, date]:
    today = datetime.now(ZoneInfo(timezone)).date()

    if date_from is None and date_to is None:
        start, end = _month_start(today), _month_end(today)
    elif date_from is None:
        start, end = _month_start(date_to), date_to
    elif date_to is None:
        start, end = date_from, today
    else:
        start, end = date_from, date_to

    if end < start:
        raise APIError(422, "invalid_date_range", "The end date must be on or after the start date.")
    if (end - start).days > MAX_RANGE_DAYS:
        raise APIError(422, "date_range_too_large", "Choose a range of two years or less.")

    return start, end


def _resolve_currency(db: Session, user_id: uuid.UUID, currency: str | None) -> str:
    if currency:
        if not profile_repository.currency_exists(db, currency):
            raise APIError(422, "unknown_currency", f"Currency {currency} is not supported.")
        return currency

    preferences = profile_repository.get_preferences(db, user_id)
    return preferences.currency_code if preferences else get_settings().default_currency


def overview(
    db: Session,
    user_id: uuid.UUID,
    timezone: str,
    date_from: date | None = None,
    date_to: date | None = None,
    currency: str | None = None,
) -> dict:
    start, end = resolve_period(timezone, date_from, date_to)
    code = _resolve_currency(db, user_id, currency)

    type_rows = report_repository.type_totals(db, user_id, code, start, end)
    income = next((amount for kind, amount, _ in type_rows if kind == "income"), 0)
    expenses = next((amount for kind, amount, _ in type_rows if kind == "expense"), 0)
    refunds = next((amount for kind, amount, _ in type_rows if kind == "refund"), 0)
    count = sum(row[2] for row in type_rows)

    spending = expenses - refunds
    net = income - spending
    savings_rate = round(net / income * 100, 1) if income > 0 else None

    buckets: dict[uuid.UUID | None, dict] = {}
    for category_id, name, kind, amount in report_repository.category_spending(
        db, user_id, code, start, end
    ):
        bucket = buckets.setdefault(
            category_id,
            {
                "category_id": str(category_id) if category_id else None,
                "name": name or "Uncategorised",
                "expense": 0,
                "refund": 0,
            },
        )
        bucket[kind] += amount

    total_spending = sum(max(bucket["expense"] - bucket["refund"], 0) for bucket in buckets.values())
    by_category = []
    for bucket in buckets.values():
        spent = bucket["expense"] - bucket["refund"]
        if spent <= 0:
            continue
        by_category.append(
            {
                "category_id": bucket["category_id"],
                "name": bucket["name"],
                "spent_minor": spent,
                "share": round(spent / total_spending * 100, 1) if total_spending else 0,
            }
        )
    by_category.sort(key=lambda row: row["spent_minor"], reverse=True)

    trend_end = _month_start(end)
    trend_start = _add_months(trend_end, -5)
    flow = {}
    for month, kind, amount in report_repository.monthly_flow(
        db, user_id, code, trend_start, _month_end(end)
    ):
        flow.setdefault((month.year, month.month), {"income": 0, "expense": 0, "refund": 0})
        flow[(month.year, month.month)][kind] += amount

    trend = []
    for offset in range(6):
        month = _add_months(trend_start, offset)
        bucket = flow.get((month.year, month.month), {"income": 0, "expense": 0, "refund": 0})
        month_spending = bucket["expense"] - bucket["refund"]
        trend.append(
            {
                "period": f"{month.year:04d}-{month.month:02d}",
                "label": month.strftime("%b %Y"),
                "income_minor": bucket["income"],
                "spending_minor": month_spending,
                "net_minor": bucket["income"] - month_spending,
            }
        )

    balances = account_repository.balances(db, user_id)
    accounts = [
        {
            "id": str(account.id),
            "name": account.name,
            "type": account.type.value,
            "currency_code": account.currency_code,
            "balance_minor": balances.get(account.id, account.opening_balance_minor),
        }
        for account in account_repository.list_for_user(db, user_id)
    ]

    recent_items, _ = transaction_repository.list_transactions(
        db,
        user_id,
        date_from=start,
        date_to=end,
        page=1,
        page_size=6,
        sort="transaction_date",
        order="desc",
    )
    from app.schemas.transaction import TransactionOut

    recent = [
        TransactionOut.model_validate(item).model_dump(mode="json") for item in recent_items
    ]

    return {
        "period": {
            "date_from": start.isoformat(),
            "date_to": end.isoformat(),
            "label": _period_label(start, end),
        },
        "currency_code": code,
        "totals": {
            "currency_code": code,
            "income_minor": income,
            "expenses_minor": expenses,
            "refunds_minor": refunds,
            "spending_minor": spending,
            "net_minor": net,
            "transaction_count": count,
            "savings_rate": savings_rate,
        },
        "by_category": by_category,
        "trend": trend,
        "accounts": accounts,
        "recent": recent,
    }


def _decimal_string(amount_minor: int, decimal_places: int) -> str:
    if decimal_places <= 0:
        return str(amount_minor)
    whole, fraction = divmod(amount_minor, 10**decimal_places)
    return f"{whole}.{fraction:0{decimal_places}d}"


def export_csv(
    db: Session,
    user_id: uuid.UUID,
    date_from: date,
    date_to: date,
    currency: str | None = None,
) -> tuple[str, str]:
    """Build a portable CSV of transactions for the period."""
    transactions = transaction_repository.export_transactions(
        db, user_id, date_from, date_to, currency
    )
    decimal_places = {
        code: places
        for code, places in db.execute(select(Currency.code, Currency.decimal_places))
    }

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "Date",
            "Type",
            "Amount",
            "Currency",
            "Vendor",
            "Description",
            "Category",
            "Account",
            "Destination account",
            "Payment method",
            "Created at (UTC)",
        ]
    )

    for transaction in transactions:
        places = decimal_places.get(transaction.currency_code, 2)
        writer.writerow(
            [
                transaction.transaction_date.isoformat(),
                transaction.type.value,
                _decimal_string(transaction.amount_minor, places),
                transaction.currency_code,
                transaction.vendor or "",
                transaction.description or "",
                transaction.category.name if transaction.category else "",
                transaction.account.name,
                transaction.destination_account.name
                if transaction.destination_account
                else "",
                transaction.payment_method.value if transaction.payment_method else "",
                transaction.created_at.isoformat(),
            ]
        )

    filename = f"transactions-{date_from.isoformat()}-to-{date_to.isoformat()}.csv"
    return buffer.getvalue(), filename
