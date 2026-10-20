"""Transaction endpoints."""

import uuid
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Header, Query

from app.api.responses import ok
from app.core.deps import CurrentUserId, DbSession
from app.models.enums import PaymentMethod, TransactionType
from app.schemas.transaction import TransactionCreate, TransactionUpdate
from app.services import transaction_service

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", summary="List transactions with filters and pagination")
def list_transactions(
    user_id: CurrentUserId,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: str | None = Query(default=None, max_length=200),
    type: TransactionType | None = Query(default=None),
    category_id: uuid.UUID | None = Query(default=None),
    account_id: uuid.UUID | None = Query(default=None),
    payment_method: PaymentMethod | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    min_amount: Annotated[int | None, Query(ge=0)] = None,
    max_amount: Annotated[int | None, Query(ge=0)] = None,
    sort: Literal["transaction_date", "amount_minor", "created_at"] = "transaction_date",
    order: Literal["asc", "desc"] = "desc",
):
    items, meta, totals = transaction_service.list_transactions(
        db,
        user_id,
        page=page,
        page_size=page_size,
        search=search,
        type=type.value if type else None,
        category_id=category_id,
        account_id=account_id,
        payment_method=payment_method.value if payment_method else None,
        date_from=date_from,
        date_to=date_to,
        min_amount=min_amount,
        max_amount=max_amount,
        sort=sort,
        order=order,
    )
    return ok(items, {**meta, "totals": totals})


@router.post("", status_code=201, summary="Create a transaction")
def create_transaction(
    user_id: CurrentUserId,
    body: TransactionCreate,
    db: DbSession,
    idempotency_key: Annotated[
        str | None, Header(alias="Idempotency-Key", max_length=255)
    ] = None,
):
    payload, status_code = transaction_service.create_transaction(
        db, user_id, body, idempotency_key
    )
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=status_code, content=payload)


@router.get("/{transaction_id}", summary="Get one transaction")
def get_transaction(transaction_id: uuid.UUID, user_id: CurrentUserId, db: DbSession):
    return ok(transaction_service.get_transaction(db, user_id, transaction_id))


@router.patch("/{transaction_id}", summary="Update a transaction")
def update_transaction(
    transaction_id: uuid.UUID,
    user_id: CurrentUserId,
    body: TransactionUpdate,
    db: DbSession,
):
    return transaction_service.update_transaction(db, user_id, transaction_id, body)


@router.delete("/{transaction_id}", summary="Soft-delete a transaction")
def delete_transaction(transaction_id: uuid.UUID, user_id: CurrentUserId, db: DbSession):
    return transaction_service.delete_transaction(db, user_id, transaction_id)
