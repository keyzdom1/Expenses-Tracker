"""Notification endpoints."""

import uuid

from fastapi import APIRouter, Query

from app.api.responses import ok
from app.core.deps import CurrentUserId, DbSession, TokenPayload
from app.services import notification_service, profile_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", summary="List notifications")
def list_notifications(
    user_id: CurrentUserId,
    payload: TokenPayload,
    db: DbSession,
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
):
    profile_service.ensure_profile(db, user_id, payload.get("email"))
    items, unread = notification_service.list_notifications(db, user_id, unread_only, limit)
    return ok(items, {"unread_count": unread})


@router.post("/read-all", summary="Mark every notification as read")
def mark_all_read(
    user_id: CurrentUserId, payload: TokenPayload, db: DbSession
):
    profile_service.ensure_profile(db, user_id, payload.get("email"))
    updated = notification_service.mark_all_read(db, user_id)
    return ok({"updated": updated})


@router.post("/{notification_id}/read", summary="Mark one notification as read")
def mark_read(
    notification_id: uuid.UUID,
    user_id: CurrentUserId,
    payload: TokenPayload,
    db: DbSession,
):
    profile_service.ensure_profile(db, user_id, payload.get("email"))
    return ok(notification_service.mark_read(db, user_id, notification_id))
