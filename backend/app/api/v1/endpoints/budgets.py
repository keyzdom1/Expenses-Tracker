"""Budget endpoints with live actuals."""

import uuid

from fastapi import APIRouter, Query

from app.api.responses import ok
from app.core.deps import CurrentUserId, DbSession, TokenPayload
from app.schemas.budget import BudgetCreate, BudgetUpdate
from app.services import budget_service, profile_service

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.get("", summary="List budgets with current-period actuals")
def list_budgets(
    user_id: CurrentUserId,
    payload: TokenPayload,
    db: DbSession,
    include_inactive: bool = Query(default=False),
):
    profile_service.ensure_profile(db, user_id, payload.get("email"))
    preferences = profile_service.get_preferences(db, user_id)
    return ok(budget_service.list_budgets(db, user_id, preferences.timezone, include_inactive))


@router.post("", status_code=201, summary="Create a budget")
def create_budget(
    user_id: CurrentUserId, payload: TokenPayload, body: BudgetCreate, db: DbSession
):
    profile_service.ensure_profile(db, user_id, payload.get("email"))
    preferences = profile_service.get_preferences(db, user_id)
    budget = budget_service.create_budget(db, user_id, preferences.timezone, body)
    return ok(budget)


@router.patch("/{budget_id}", summary="Update a budget")
def update_budget(
    budget_id: uuid.UUID,
    user_id: CurrentUserId,
    payload: TokenPayload,
    body: BudgetUpdate,
    db: DbSession,
):
    profile_service.ensure_profile(db, user_id, payload.get("email"))
    preferences = profile_service.get_preferences(db, user_id)
    budget = budget_service.update_budget(db, user_id, preferences.timezone, budget_id, body)
    return ok(budget)


@router.delete("/{budget_id}", summary="Delete a budget")
def delete_budget(budget_id: uuid.UUID, user_id: CurrentUserId, db: DbSession):
    budget_service.delete_budget(db, user_id, budget_id)
    return ok({"id": str(budget_id), "deleted": True})
