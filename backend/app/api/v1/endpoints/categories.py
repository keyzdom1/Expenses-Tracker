"""Category endpoints."""

import uuid

from fastapi import APIRouter, Query

from app.api.responses import ok
from app.core.deps import CurrentUserId, DbSession
from app.models.enums import CategoryKind
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate
from app.services import category_service

router = APIRouter(prefix="/categories", tags=["categories"])


def _out(category) -> dict:
    return CategoryOut.model_validate(category).model_dump(mode="json")


@router.get("", summary="List categories")
def list_categories(
    user_id: CurrentUserId,
    db: DbSession,
    kind: CategoryKind | None = Query(default=None),
):
    categories = category_service.list_categories(db, user_id, kind.value if kind else None)
    return ok([_out(category) for category in categories])


@router.post("", status_code=201, summary="Create a category")
def create_category(user_id: CurrentUserId, body: CategoryCreate, db: DbSession):
    category = category_service.create_category(
        db, user_id, body.name, body.kind, body.parent_id
    )
    return ok(_out(category))


@router.patch("/{category_id}", summary="Update a category")
def update_category(
    category_id: uuid.UUID, user_id: CurrentUserId, body: CategoryUpdate, db: DbSession
):
    category = category_service.update_category(
        db, user_id, category_id, body.model_dump(exclude_unset=True)
    )
    return ok(_out(category))


@router.delete("/{category_id}", summary="Delete an unused category")
def delete_category(category_id: uuid.UUID, user_id: CurrentUserId, db: DbSession):
    category_service.delete_category(db, user_id, category_id)
    return ok({"id": str(category_id), "deleted": True})
