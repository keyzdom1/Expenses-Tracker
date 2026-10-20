"""Account endpoints."""

import uuid

from fastapi import APIRouter, Query

from app.api.responses import ok
from app.core.deps import CurrentUserId, DbSession
from app.schemas.account import AccountCreate, AccountOut, AccountUpdate
from app.services import account_service

router = APIRouter(prefix="/accounts", tags=["accounts"])


def _out(account, balance: int) -> dict:
    return AccountOut(
        id=account.id,
        name=account.name,
        type=account.type,
        currency_code=account.currency_code,
        opening_balance_minor=account.opening_balance_minor,
        balance_minor=balance,
        is_active=account.is_active,
        archived_at=account.archived_at,
        created_at=account.created_at,
    ).model_dump(mode="json")


@router.get("", summary="List accounts with derived balances")
def list_accounts(
    user_id: CurrentUserId,
    db: DbSession,
    include_archived: bool = Query(default=False),
):
    pairs = account_service.list_accounts(db, user_id, include_archived)
    return ok([_out(account, balance) for account, balance in pairs])


@router.post("", status_code=201, summary="Create an account")
def create_account(user_id: CurrentUserId, body: AccountCreate, db: DbSession):
    account = account_service.create_account(db, user_id, body.model_dump())
    return ok(_out(account, account.opening_balance_minor))


@router.get("/{account_id}", summary="Get one account")
def get_account(account_id: uuid.UUID, user_id: CurrentUserId, db: DbSession):
    account = account_service.get_account(db, user_id, account_id)
    balance = account_service.get_balance(db, user_id, account_id)
    return ok(_out(account, balance))


@router.patch("/{account_id}", summary="Update an account")
def update_account(
    account_id: uuid.UUID, user_id: CurrentUserId, body: AccountUpdate, db: DbSession
):
    account = account_service.update_account(
        db, user_id, account_id, body.model_dump(exclude_unset=True)
    )
    balance = account_service.get_balance(db, user_id, account_id)
    return ok(_out(account, balance))


@router.delete("/{account_id}", summary="Archive an account")
def archive_account(account_id: uuid.UUID, user_id: CurrentUserId, db: DbSession):
    account = account_service.archive_account(db, user_id, account_id)
    balance = account_service.get_balance(db, user_id, account_id)
    return ok(_out(account, balance))
