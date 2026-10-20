"""Dashboard reporting endpoints."""

from datetime import date

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.api.responses import ok
from app.core.deps import CurrentUserId, DbSession, TokenPayload
from app.services import profile_service, report_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/overview", summary="Authoritative dashboard overview")
def overview(
    user_id: CurrentUserId,
    payload: TokenPayload,
    db: DbSession,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    currency: str | None = Query(default=None, min_length=3, max_length=3),
):
    profile_service.ensure_profile(db, user_id, payload.get("email"))
    preferences = profile_service.get_preferences(db, user_id)
    data = report_service.overview(
        db,
        user_id,
        preferences.timezone,
        date_from=date_from,
        date_to=date_to,
        currency=currency.upper() if currency else None,
    )
    return ok(data)


@router.get("/transactions.csv", summary="Export transactions as CSV")
def export_transactions(
    user_id: CurrentUserId,
    payload: TokenPayload,
    db: DbSession,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    currency: str | None = Query(default=None, min_length=3, max_length=3),
):
    profile_service.ensure_profile(db, user_id, payload.get("email"))
    preferences = profile_service.get_preferences(db, user_id)
    start, end = report_service.resolve_period(preferences.timezone, date_from, date_to)
    content, filename = report_service.export_csv(
        db, user_id, start, end, currency.upper() if currency else None
    )

    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
