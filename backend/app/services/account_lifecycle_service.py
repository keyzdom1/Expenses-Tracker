"""User data export and account deletion.

Export returns portable JSON metadata (receipt files themselves stay in private
storage; their storage paths and metadata are included). Deletion removes all
owned rows through the profile cascade and, when the service-role key is set,
also deletes the Supabase Auth user.
"""

import enum
import json
import logging
import uuid
from datetime import date, datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import APIError
from app.models.account import Account
from app.models.audit import AuditLog, IdempotencyKey
from app.models.budget import Budget, SavingsGoal
from app.models.category import Category
from app.models.notification import Notification
from app.models.profile import Profile, UserPreferences
from app.models.receipt import Receipt
from app.models.recurring import Bill, RecurringTransaction
from app.models.transaction import Tag, Transaction, TransactionTag
from app.services import receipt_storage

logger = logging.getLogger("expense_tracker.account")

USER_MODELS = (
    ("accounts", Account),
    ("categories", Category),
    ("tags", Tag),
    ("transactions", Transaction),
    ("receipts", Receipt),
    ("budgets", Budget),
    ("savings_goals", SavingsGoal),
    ("recurring_transactions", RecurringTransaction),
    ("bills", Bill),
    ("notifications", Notification),
    ("audit_logs", AuditLog),
    ("idempotency_keys", IdempotencyKey),
)


def _json_value(value):
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat() if value.tzinfo else value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, enum.Enum):
        return value.value
    return value


def _serialize(row) -> dict:
    return {
        column.key: _json_value(getattr(row, column.key))
        for column in row.__table__.columns
    }


def export_data(db: Session, user_id: uuid.UUID) -> dict:
    """Everything the user owns, suitable for a JSON download."""
    profile = db.get(Profile, user_id)
    if profile is None:
        raise APIError(404, "not_found", "Profile not found.")

    preferences = db.scalar(
        select(UserPreferences).where(UserPreferences.user_id == user_id)
    )

    tables = {}
    for name, model in USER_MODELS:
        rows = db.scalars(select(model).where(model.user_id == user_id)).all()
        tables[name] = [_serialize(row) for row in rows]

    tag_links = db.execute(
        select(TransactionTag)
        .join(Transaction, Transaction.id == TransactionTag.transaction_id)
        .where(Transaction.user_id == user_id)
    ).scalars()
    tables["transaction_tags"] = [_serialize(row) for row in tag_links]

    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "profile": _serialize(profile),
        "preferences": _serialize(preferences) if preferences else None,
        "tables": tables,
    }


def export_json(db: Session, user_id: uuid.UUID) -> tuple[str, str]:
    data = export_data(db, user_id)
    filename = f"expense-tracker-export-{date.today().isoformat()}.json"
    return json.dumps(data, indent=2, ensure_ascii=False), filename


def _delete_auth_user(user_id: uuid.UUID) -> bool:
    """Delete the Supabase Auth user when server credentials are available."""
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return False

    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users/{user_id}"
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
    }
    try:
        response = httpx.delete(url, headers=headers, timeout=30)
    except httpx.HTTPError as exc:
        raise APIError(
            502,
            "auth_delete_failed",
            "Could not delete the sign-in account. Please try again.",
        ) from exc

    if response.status_code == 404:
        return True  # Already gone; treat as success.
    if response.status_code >= 400:
        raise APIError(
            502,
            "auth_delete_failed",
            "Could not delete the sign-in account. Please try again.",
            {"status": response.status_code},
        )
    return True


def delete_account(db: Session, user_id: uuid.UUID) -> dict:
    profile = db.get(Profile, user_id)
    if profile is None:
        raise APIError(404, "not_found", "Profile not found.")

    auth_deleted = _delete_auth_user(user_id)

    receipts = db.scalars(select(Receipt).where(Receipt.user_id == user_id)).all()
    for receipt in receipts:
        try:
            receipt_storage.delete(receipt.storage_path)
        except APIError:
            logger.warning("Could not remove receipt object during account deletion")

    db.delete(profile)
    db.commit()

    return {"deleted": True, "auth_user_deleted": auth_deleted}
