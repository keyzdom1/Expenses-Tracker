"""Bill endpoints."""

import uuid
from datetime import date

from fastapi import APIRouter, Query

from app.api.responses import ok
from app.core.deps import CurrentUserId, DbSession, TokenPayload
from app.models.enums import BillStatus
from app.services import bill_service, profile_service

router = APIRouter(prefix="/bills", tags=["bills"])


@router.get("", summary="List bill occurrences")
def list_bills(
    user_id: CurrentUserId,
    payload: TokenPayload,
    db: DbSession,
    status: BillStatus | None = Query(default=None),
    due_from: date | None = Query(default=None),
    due_to: date | None = Query(default=None),
):
    profile_service.ensure_profile(db, user_id, payload.get("email"))
    return ok(
        bill_service.list_bills(
            db,
            user_id,
            status=status.value if status else None,
            due_from=due_from,
            due_to=due_to,
        )
    )


@router.post("/{bill_id}/pay", summary="Record a bill as paid")
def pay_bill(
    bill_id: uuid.UUID, user_id: CurrentUserId, payload: TokenPayload, db: DbSession
):
    profile_service.ensure_profile(db, user_id, payload.get("email"))
    return ok(bill_service.pay_bill(db, user_id, bill_id))


@router.post("/{bill_id}/skip", summary="Skip a bill")
def skip_bill(
    bill_id: uuid.UUID, user_id: CurrentUserId, payload: TokenPayload, db: DbSession
):
    profile_service.ensure_profile(db, user_id, payload.get("email"))
    return ok(bill_service.skip_bill(db, user_id, bill_id))
