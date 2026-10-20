"""Current user profile and preferences."""

from fastapi import APIRouter
from fastapi.responses import Response

from app.api.responses import ok
from app.core.deps import CurrentUserId, DbSession, TokenPayload
from app.core.errors import APIError
from app.schemas.profile import (
    AccountDeleteRequest,
    PreferencesOut,
    PreferencesUpdate,
    ProfileOut,
    ProfileUpdate,
)
from app.services import account_lifecycle_service, profile_service

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", summary="Get the current user's profile")
def get_me(user_id: CurrentUserId, payload: TokenPayload, db: DbSession):
    profile = profile_service.ensure_profile(db, user_id, payload.get("email"))
    return ok(ProfileOut.model_validate(profile).model_dump(mode="json"))


@router.patch("", summary="Update the current user's profile")
def update_me(user_id: CurrentUserId, payload: TokenPayload, body: ProfileUpdate, db: DbSession):
    profile_service.ensure_profile(db, user_id, payload.get("email"))
    profile = profile_service.update_profile(db, user_id, body.model_dump(exclude_unset=True))
    return ok(ProfileOut.model_validate(profile).model_dump(mode="json"))


@router.get("/export", summary="Download all of the current user's data")
def export_my_data(user_id: CurrentUserId, payload: TokenPayload, db: DbSession):
    profile_service.ensure_profile(db, user_id, payload.get("email"))
    content, filename = account_lifecycle_service.export_json(db, user_id)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("", summary="Delete the current user's account and data")
def delete_my_account(
    user_id: CurrentUserId,
    payload: TokenPayload,
    body: AccountDeleteRequest,
    db: DbSession,
):
    profile_service.ensure_profile(db, user_id, payload.get("email"))
    if body.confirm != "DELETE":
        raise APIError(
            422,
            "confirmation_required",
            'Type DELETE to confirm account deletion.',
        )
    return ok(account_lifecycle_service.delete_account(db, user_id))


@router.get("/preferences", summary="Get the current user's preferences")
def get_preferences(user_id: CurrentUserId, payload: TokenPayload, db: DbSession):
    # Safe if this is the user's very first request (e.g. ThemeSync runs in
    # parallel with GET /me): the profile and default preferences are created.
    profile_service.ensure_profile(db, user_id, payload.get("email"))
    preferences = profile_service.get_preferences(db, user_id)
    return ok(PreferencesOut.model_validate(preferences).model_dump(mode="json"))


@router.patch("/preferences", summary="Update the current user's preferences")
def update_preferences(
    user_id: CurrentUserId, payload: TokenPayload, body: PreferencesUpdate, db: DbSession
):
    profile_service.ensure_profile(db, user_id, payload.get("email"))
    preferences = profile_service.update_preferences(
        db, user_id, body.model_dump(exclude_unset=True)
    )
    return ok(PreferencesOut.model_validate(preferences).model_dump(mode="json"))
