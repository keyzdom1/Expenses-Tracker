"""Budget business rules and live actuals."""

import calendar
import uuid
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import APIError
from app.models.budget import Budget
from app.models.enums import BudgetPeriod, CategoryKind
from app.repositories import (
    budget_repository,
    category_repository,
    profile_repository,
    report_repository,
)
from app.schemas.budget import BudgetCreate, BudgetUpdate


def _today(timezone: str) -> date:
    return datetime.now(ZoneInfo(timezone)).date()


def _month_end(value: date) -> date:
    return value.replace(day=calendar.monthrange(value.year, value.month)[1])


def period_window(budget: Budget, today: date) -> tuple[date, date]:
    """The window a recurring budget measures right now."""
    if budget.period == BudgetPeriod.CUSTOM:
        start = budget.start_date
        end = budget.end_date or _month_end(start)
        return start, end

    if budget.period == BudgetPeriod.WEEKLY:
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=6)

    if budget.period == BudgetPeriod.MONTHLY:
        return today.replace(day=1), _month_end(today)

    if budget.period == BudgetPeriod.QUARTERLY:
        first_month = (today.month - 1) // 3 * 3 + 1
        start = date(today.year, first_month, 1)
        end_month = first_month + 2
        return start, _month_end(date(today.year, end_month, 1))

    return date(today.year, 1, 1), date(today.year, 12, 31)


def _state(percent: float, warning: int, critical: int) -> str:
    if percent >= 100:
        return "exceeded"
    if percent >= critical:
        return "critical"
    if percent >= warning:
        return "warning"
    return "ok"


def _resolve_category(
    db: Session, user_id: uuid.UUID, category_id: uuid.UUID | None
) -> str | None:
    if category_id is None:
        return None

    category = category_repository.get(db, user_id, category_id)
    if category is None:
        raise APIError(404, "not_found", "Category not found.")
    if category.kind != CategoryKind.EXPENSE:
        raise APIError(422, "category_kind_mismatch", "Budgets track expense categories.")
    return category.name


def _resolve_currency(db: Session, user_id: uuid.UUID, currency: str | None) -> str:
    if currency is None:
        preferences = profile_repository.get_preferences(db, user_id)
        return preferences.currency_code if preferences else get_settings().default_currency
    if not profile_repository.currency_exists(db, currency):
        raise APIError(422, "unknown_currency", f"Currency {currency} is not supported.")
    return currency


def _serialize(
    budget: Budget, category_name: str | None, spent: int, today: date
) -> dict:
    period_start, period_end = period_window(budget, today)
    percent = round(spent / budget.amount_minor * 100, 1) if budget.amount_minor else 0.0

    return {
        "id": str(budget.id),
        "name": budget.name,
        "category_id": str(budget.category_id) if budget.category_id else None,
        "category_name": category_name,
        "amount_minor": budget.amount_minor,
        "currency_code": budget.currency_code,
        "period": budget.period.value,
        "start_date": budget.start_date.isoformat(),
        "end_date": budget.end_date.isoformat() if budget.end_date else None,
        "warning_threshold": budget.warning_threshold,
        "critical_threshold": budget.critical_threshold,
        "is_active": budget.is_active,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "spent_minor": spent,
        "remaining_minor": budget.amount_minor - spent,
        "percent_used": percent,
        "state": _state(percent, budget.warning_threshold, budget.critical_threshold),
    }


def _spent_for(db: Session, user_id: uuid.UUID, budget: Budget, today: date) -> int:
    start, end = period_window(budget, today)
    return report_repository.budget_spent(
        db, user_id, budget.currency_code, start, end, budget.category_id
    )


def list_budgets(db: Session, user_id: uuid.UUID, timezone: str, include_inactive: bool = False):
    today = _today(timezone)
    budgets = budget_repository.list_for_user(db, user_id, include_inactive)
    category_names = {
        category.id: category.name
        for category in category_repository.list_for_user(db, user_id, CategoryKind.EXPENSE.value)
    }
    return [
        _serialize(budget, category_names.get(budget.category_id), _spent_for(db, user_id, budget, today), today)
        for budget in budgets
    ]


def get_budget(db: Session, user_id: uuid.UUID, budget_id: uuid.UUID) -> Budget:
    budget = budget_repository.get(db, user_id, budget_id)
    if budget is None:
        raise APIError(404, "not_found", "Budget not found.")
    return budget


def create_budget(
    db: Session, user_id: uuid.UUID, timezone: str, data: BudgetCreate
) -> dict:
    today = _today(timezone)
    category_name = _resolve_category(db, user_id, data.category_id)
    currency = _resolve_currency(db, user_id, data.currency_code)

    budget = Budget(
        user_id=user_id,
        name=data.name,
        category_id=data.category_id,
        amount_minor=data.amount_minor,
        currency_code=currency,
        period=data.period,
        start_date=data.start_date or today.replace(day=1),
        end_date=data.end_date,
        warning_threshold=data.warning_threshold,
        critical_threshold=data.critical_threshold,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)

    return _serialize(budget, category_name, _spent_for(db, user_id, budget, today), today)


def update_budget(
    db: Session, user_id: uuid.UUID, timezone: str, budget_id: uuid.UUID, data: BudgetUpdate
) -> dict:
    budget = get_budget(db, user_id, budget_id)
    changes = data.model_dump(exclude_unset=True)
    today = _today(timezone)

    # These columns are NOT NULL; treat an explicit null as "leave unchanged".
    for required in ("name", "amount_minor", "period", "currency_code"):
        if required in changes and changes[required] is None:
            changes.pop(required)

    period = changes.get("period", budget.period)
    warning = changes.get("warning_threshold", budget.warning_threshold)
    critical = changes.get("critical_threshold", budget.critical_threshold)
    start_date = changes.get("start_date", budget.start_date)
    end_date = changes.get("end_date", budget.end_date)

    if warning > critical:
        raise APIError(422, "thresholds_ordered", "The warning threshold must not exceed critical.")
    if period == BudgetPeriod.CUSTOM and end_date is None:
        raise APIError(422, "end_date_required", "A custom budget needs an end date.")
    if end_date and start_date and end_date < start_date:
        raise APIError(422, "invalid_date_range", "The end date must be on or after the start date.")

    category_id = changes.get("category_id", budget.category_id)
    category_name = _resolve_category(db, user_id, category_id)

    if "currency_code" in changes and changes["currency_code"] is not None:
        _resolve_currency(db, user_id, changes["currency_code"])

    for field, value in changes.items():
        setattr(budget, field, value)

    db.commit()
    db.refresh(budget)

    return _serialize(budget, category_name, _spent_for(db, user_id, budget, today), today)


def delete_budget(db: Session, user_id: uuid.UUID, budget_id: uuid.UUID) -> None:
    budget = get_budget(db, user_id, budget_id)
    db.delete(budget)
    db.commit()
