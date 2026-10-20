"""Tag endpoints."""

import uuid

from fastapi import APIRouter
from sqlalchemy.exc import IntegrityError

from app.api.responses import ok
from app.core.deps import CurrentUserId, DbSession
from app.core.errors import APIError
from app.models.transaction import Tag
from app.repositories import tag_repository
from app.schemas.tag import TagCreate, TagOut

router = APIRouter(prefix="/tags", tags=["tags"])


def _out(tag: Tag) -> dict:
    return TagOut.model_validate(tag).model_dump(mode="json")


@router.get("", summary="List tags")
def list_tags(user_id: CurrentUserId, db: DbSession):
    return ok([_out(tag) for tag in tag_repository.list_for_user(db, user_id)])


@router.post("", status_code=201, summary="Create a tag")
def create_tag(user_id: CurrentUserId, body: TagCreate, db: DbSession):
    if tag_repository.name_exists(db, user_id, body.name):
        raise APIError(409, "duplicate_tag", "A tag with that name already exists.")

    tag = Tag(user_id=user_id, name=body.name, color=body.color)
    db.add(tag)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise APIError(409, "duplicate_tag", "A tag with that name already exists.") from exc

    db.refresh(tag)
    return ok(_out(tag))


@router.delete("/{tag_id}", summary="Delete a tag")
def delete_tag(tag_id: uuid.UUID, user_id: CurrentUserId, db: DbSession):
    tag = tag_repository.get(db, user_id, tag_id)
    if tag is None:
        raise APIError(404, "not_found", "Tag not found.")

    db.delete(tag)
    db.commit()
    return ok({"id": str(tag_id), "deleted": True})
