"""Scheduled job trigger for bills, overdue checks and notifications."""

import hmac
from typing import Annotated

from fastapi import APIRouter, Header

from app.api.responses import ok
from app.core.config import get_settings
from app.core.deps import CurrentUserId, DbSession, TokenPayload
from app.core.errors import APIError
from app.services import job_service, profile_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/run/me", summary="Run the daily job for the signed-in user")
def run_my_jobs(
    user_id: CurrentUserId, payload: TokenPayload, db: DbSession
):
    """On-demand generation so new templates show their bills immediately."""
    profile_service.ensure_profile(db, user_id, payload.get("email"))
    return ok(job_service.run(db, user_id=user_id))


@router.post("/run", summary="Run the idempotent daily job")
def run_jobs(
    db: DbSession,
    x_cron_secret: Annotated[str | None, Header(alias="X-Cron-Secret")] = None,
):
    settings = get_settings()

    if settings.cron_secret:
        if not x_cron_secret or not hmac.compare_digest(x_cron_secret, settings.cron_secret):
            raise APIError(401, "invalid_cron_secret", "A valid cron secret is required.")
    elif settings.is_production:
        raise APIError(403, "cron_not_configured", "Set CRON_SECRET before enabling jobs.")

    return ok(job_service.run(db))
