"""Transaction business rules: validation, idempotency, audit and totals."""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.models.audit import AuditLog, IdempotencyKey
from app.models.category import Category
from app.models.enums import CategoryKind, TransactionType
from app.models.transaction import Transaction
from app.repositories import (
    account_repository,
    category_repository,
    tag_repository,
    transaction_repository,
)
from app.schemas.transaction import TransactionCreate, TransactionOut, TransactionUpdate


def _serialize(transaction: Transaction) -> dict[str, Any]:
    return TransactionOut.model_validate(transaction).model_dump(mode="json")


def _payload_hash(data: dict[str, Any]) -> str:
    encoded = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _audit(db: Session, user_id: uuid.UUID, entity_id: uuid.UUID, action: str, changes: dict):
    db.add(
        AuditLog(
            user_id=user_id,
            entity_type="transaction",
            entity_id=entity_id,
            action=action,
            changes=changes,
        )
    )


def _resolve_category(
    db: Session, user_id: uuid.UUID, category_id: uuid.UUID | None, tx_type: TransactionType
) -> Category | None:
    if tx_type == TransactionType.TRANSFER:
        if category_id is not None:
            raise APIError(422, "category_not_allowed", "Transfers cannot have a category.")
        return None

    if category_id is None:
        return None

    category = category_repository.get(db, user_id, category_id)
    if category is None:
        raise APIError(404, "not_found", "Category not found.")

    expected = CategoryKind.INCOME if tx_type == TransactionType.INCOME else CategoryKind.EXPENSE
    if category.kind != expected:
        raise APIError(
            422,
            "category_kind_mismatch",
            f"A {tx_type.value} needs a {expected.value} category.",
        )
    return category


def _resolve_accounts(
    db: Session,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
    dest_account_id: uuid.UUID | None,
    tx_type: TransactionType,
    currency_code: str | None,
) -> tuple:
    account = account_repository.get(db, user_id, account_id)
    if account is None:
        raise APIError(404, "not_found", "Account not found.")
    if not account.is_active:
        raise APIError(422, "account_archived", "This account is archived.")

    if tx_type == TransactionType.TRANSFER:
        if dest_account_id is None:
            raise APIError(422, "transfer_destination_required", "Choose a destination account.")
        if dest_account_id == account_id:
            raise APIError(422, "transfer_same_account", "Choose a different destination account.")

        destination = account_repository.get(db, user_id, dest_account_id)
        if destination is None:
            raise APIError(404, "not_found", "Destination account not found.")
        if not destination.is_active:
            raise APIError(422, "account_archived", "The destination account is archived.")
        if destination.currency_code != account.currency_code:
            raise APIError(
                422,
                "currency_mismatch",
                "Transfers between different currencies are not supported.",
            )
    else:
        if dest_account_id is not None:
            raise APIError(
                422, "destination_not_allowed", "Only transfers can have a destination account."
            )
        destination = None

    if currency_code and currency_code != account.currency_code:
        raise APIError(
            422,
            "currency_mismatch",
            f"This account uses {account.currency_code}, not {currency_code}.",
        )

    return account, destination


def _resolve_refund(
    db: Session,
    user_id: uuid.UUID,
    refund_of_id: uuid.UUID | None,
    tx_type: TransactionType,
    currency_code: str,
) -> Transaction | None:
    if refund_of_id is None:
        return None

    if tx_type != TransactionType.REFUND:
        raise APIError(422, "refund_link_invalid", "Only refunds can reference another transaction.")

    original = transaction_repository.get(db, user_id, refund_of_id)
    if original is None:
        raise APIError(404, "not_found", "Original transaction not found.")
    if original.type != TransactionType.EXPENSE:
        raise APIError(422, "refund_link_invalid", "A refund must reference an expense.")
    if original.currency_code != currency_code:
        raise APIError(422, "currency_mismatch", "The refund currency must match the expense.")
    return original


def _resolve_tags(db: Session, user_id: uuid.UUID, tag_ids: list[uuid.UUID]) -> list:
    unique_ids = list(dict.fromkeys(tag_ids))
    tags = tag_repository.get_many(db, user_id, unique_ids)
    if len(tags) != len(unique_ids):
        raise APIError(404, "not_found", "One or more tags were not found.")
    return tags


def _resolve_all(db: Session, user_id: uuid.UUID, values: dict[str, Any]) -> dict[str, Any]:
    tx_type: TransactionType = values["type"]
    account, destination = _resolve_accounts(
        db,
        user_id,
        values["account_id"],
        values.get("dest_account_id"),
        tx_type,
        values.get("currency_code"),
    )
    category = _resolve_category(db, user_id, values.get("category_id"), tx_type)
    _resolve_refund(db, user_id, values.get("refund_of_id"), tx_type, account.currency_code)
    tags = _resolve_tags(db, user_id, values.get("tag_ids") or [])

    return {
        "account": account,
        "destination": destination,
        "category": category,
        "tags": tags,
        "currency_code": account.currency_code,
    }


def create_transaction(
    db: Session,
    user_id: uuid.UUID,
    data: TransactionCreate,
    idempotency_key: str | None = None,
) -> tuple[dict[str, Any], int]:
    payload = data.model_dump(mode="python")
    json_payload = data.model_dump(mode="json")
    request_hash = _payload_hash(json_payload)

    if idempotency_key:
        existing = db.scalar(
            select(IdempotencyKey).where(
                IdempotencyKey.user_id == user_id, IdempotencyKey.key == idempotency_key
            )
        )
        if existing is not None:
            if existing.request_hash != request_hash:
                raise APIError(
                    409,
                    "idempotency_conflict",
                    "This Idempotency-Key was already used with a different request.",
                )
            return existing.response_body or {}, existing.status_code

    resolved = _resolve_all(db, user_id, payload)

    transaction = Transaction(
        user_id=user_id,
        account_id=resolved["account"].id,
        dest_account_id=resolved["destination"].id if resolved["destination"] else None,
        category_id=resolved["category"].id if resolved["category"] else None,
        type=data.type,
        amount_minor=data.amount_minor,
        currency_code=resolved["currency_code"],
        transaction_date=data.transaction_date,
        occurred_at=data.occurred_at,
        payment_method=data.payment_method,
        vendor=data.vendor,
        description=data.description,
        refund_of_id=data.refund_of_id,
    )
    transaction.tags = resolved["tags"]

    db.add(transaction)
    db.flush()
    db.refresh(transaction)

    body = {"data": _serialize(transaction), "meta": {}}
    _audit(db, user_id, transaction.id, "create", json_payload)

    if idempotency_key:
        db.add(
            IdempotencyKey(
                user_id=user_id,
                key=idempotency_key,
                request_hash=request_hash,
                status_code=201,
                response_body=body,
            )
        )

    try:
        db.commit()
    except IntegrityError:
        # Two concurrent requests with the same key: return the winner's result.
        db.rollback()
        if idempotency_key:
            existing = db.scalar(
                select(IdempotencyKey).where(
                    IdempotencyKey.user_id == user_id, IdempotencyKey.key == idempotency_key
                )
            )
            if existing is not None and existing.request_hash == request_hash:
                return existing.response_body or {}, existing.status_code
        raise

    return body, 201


def update_transaction(
    db: Session, user_id: uuid.UUID, transaction_id: uuid.UUID, data: TransactionUpdate
) -> dict[str, Any]:
    transaction = transaction_repository.get(db, user_id, transaction_id)
    if transaction is None:
        raise APIError(404, "not_found", "Transaction not found.")

    changes = data.model_dump(exclude_unset=True)

    merged: dict[str, Any] = {
        "type": transaction.type,
        "account_id": transaction.account_id,
        "dest_account_id": transaction.dest_account_id,
        "category_id": transaction.category_id,
        "currency_code": transaction.currency_code,
        "refund_of_id": transaction.refund_of_id,
        "tag_ids": [tag.id for tag in transaction.tags],
    }
    merged.update(changes)

    # Changing the account without naming a currency adopts that account's currency.
    if "account_id" in changes and "currency_code" not in changes:
        merged["currency_code"] = None
    # Leaving transfer mode clears the destination (the DB constraint requires it).
    if merged["type"] != TransactionType.TRANSFER and "dest_account_id" not in changes:
        merged["dest_account_id"] = None
    if merged["type"] == TransactionType.TRANSFER and "category_id" not in changes:
        merged["category_id"] = None
    if merged["type"] != TransactionType.REFUND and "refund_of_id" not in changes:
        merged["refund_of_id"] = None

    resolved = _resolve_all(db, user_id, merged)

    transaction.type = merged["type"]
    transaction.account_id = resolved["account"].id
    transaction.dest_account_id = resolved["destination"].id if resolved["destination"] else None
    transaction.category_id = resolved["category"].id if resolved["category"] else None
    transaction.currency_code = resolved["currency_code"]
    transaction.tags = resolved["tags"]

    for field in (
        "amount_minor",
        "transaction_date",
        "occurred_at",
        "payment_method",
        "vendor",
        "description",
        "refund_of_id",
    ):
        if field in changes:
            setattr(transaction, field, changes[field])

    _audit(
        db,
        user_id,
        transaction.id,
        "update",
        data.model_dump(mode="json", exclude_unset=True),
    )
    db.commit()
    db.refresh(transaction)

    return {"data": _serialize(transaction), "meta": {}}


def delete_transaction(db: Session, user_id: uuid.UUID, transaction_id: uuid.UUID) -> dict[str, Any]:
    transaction = transaction_repository.get(db, user_id, transaction_id)
    if transaction is None:
        raise APIError(404, "not_found", "Transaction not found.")

    transaction.deleted_at = datetime.now(timezone.utc)
    _audit(db, user_id, transaction.id, "delete", {"deleted_at": transaction.deleted_at.isoformat()})
    db.commit()

    return {"data": {"id": str(transaction.id), "deleted_at": transaction.deleted_at.isoformat()}}


def get_transaction(db: Session, user_id: uuid.UUID, transaction_id: uuid.UUID) -> dict[str, Any]:
    transaction = transaction_repository.get(db, user_id, transaction_id)
    if transaction is None:
        raise APIError(404, "not_found", "Transaction not found.")
    return _serialize(transaction)


def _summarise(rows: list[tuple[str, str, int, int]]) -> list[dict[str, Any]]:
    per_currency: dict[str, dict[str, int]] = {}
    for currency, tx_type, amount, count in rows:
        # Transfers only move money between accounts; they are never income
        # or spending, so they are excluded from totals entirely.
        if tx_type == "transfer":
            continue
        bucket = per_currency.setdefault(
            currency,
            {"income": 0, "expense": 0, "refund": 0, "count": 0},
        )
        if tx_type in bucket:
            bucket[tx_type] += amount
        bucket["count"] += count

    result = []
    for currency, bucket in sorted(per_currency.items()):
        spending = bucket["expense"] - bucket["refund"]
        result.append(
            {
                "currency_code": currency,
                "income_minor": bucket["income"],
                "expenses_minor": bucket["expense"],
                "refunds_minor": bucket["refund"],
                "spending_minor": spending,
                "net_minor": bucket["income"] - spending,
                "transaction_count": bucket["count"],
            }
        )
    return result


def list_transactions(db: Session, user_id: uuid.UUID, **filters) -> tuple[list, dict, list]:
    page = max(1, filters.get("page") or 1)
    page_size = min(100, max(1, filters.get("page_size") or 20))

    query_filters = {
        "search": filters.get("search"),
        "type": filters.get("type"),
        "category_id": filters.get("category_id"),
        "account_id": filters.get("account_id"),
        "payment_method": filters.get("payment_method"),
        "date_from": filters.get("date_from"),
        "date_to": filters.get("date_to"),
        "min_amount": filters.get("min_amount"),
        "max_amount": filters.get("max_amount"),
    }

    items, total = transaction_repository.list_transactions(
        db,
        user_id,
        **query_filters,
        sort=filters.get("sort") or "transaction_date",
        order=filters.get("order") or "desc",
        page=page,
        page_size=page_size,
    )

    from app.schemas.common import PageMeta

    meta = PageMeta.build(page, page_size, total).model_dump()
    totals = _summarise(transaction_repository.totals(db, user_id, **query_filters))
    return [_serialize(item) for item in items], meta, totals
