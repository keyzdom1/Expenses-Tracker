"""Recurring transaction endpoints."""

import uuid

from fastapi import APIRouter, Query

from app.api.responses import ok
from app.core.deps import CurrentUserId, DbSession, TokenPayload
from app.schemas.recurring import RecurringCreate, RecurringUpdate
from app.services import profile_service, recurring_service

router = APIRouter(prefix="/recurring", tags=["recurring"])


@router.get("", summary="List recurring templates")
def list_recurring(
    user_id: CurrentUserId,
    payload: TokenPayload,
    db: DbSession,
    include_inactive: bool = Query(default=False),
):
    profile_service.ensure_profile(db, user_id, payload.get("email"))
    return ok(recurring_service.list_recurring(db, user_id, include_inactive))


@router.post("", status_code=201, summary="Create a recurring template")
def create_recurring(
    user_id: CurrentUserId, payload: TokenPayload, body: RecurringCreate, db: DbSession
):
    profile_service.ensure_profile(db, user_id, payload.get("email"))
    return ok(recurring_service.create_recurring(db, user_id, body))


@router.patch("/{recurring_id}", summary="Update a recurring template")
def update_recurring(
    recurring_id: uuid.UUID,
    user_id: CurrentUserId,
    payload: TokenPayload,
    body: RecurringUpdate,
    db: DbSession,
):
    profile_service.ensure_profile(db, user_id, payload.get("email"))
    return ok(recurring_service.update_recurring(db, user_id, recurring_id, body))


@router.delete("/{recurring_id}", summary="Pause a recurring template")
def deactivate_recurring(
    recurring_id: uuid.UUID, user_id: CurrentUserId, payload: TokenPayload, db: DbSession
):
    profile_service.ensure_profile(db, user_id, payload.get("email"))
    return ok(recurring_service.deactivate_recurring(db, user_id, recurring_id))
