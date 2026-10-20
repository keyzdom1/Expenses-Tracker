"""User isolation: one user's token can never expose another user's data."""

import uuid

from sqlalchemy import func, select, text

from app.models.profile import Profile, UserPreferences
from tests.conftest import engine


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_tokens_resolve_to_distinct_profiles(client, db, make_token):
    user_a, user_b = uuid.uuid4(), uuid.uuid4()
    token_a = make_token(user_a, email="a@example.com")
    token_b = make_token(user_b, email="b@example.com")

    response_a = client.get("/api/v1/me", headers=auth_header(token_a))
    response_b = client.get("/api/v1/me", headers=auth_header(token_b))

    assert response_a.json()["data"]["id"] == str(user_a)
    assert response_b.json()["data"]["id"] == str(user_b)
    assert db.scalar(select(func.count()).select_from(Profile)) == 2


def test_updating_one_profile_does_not_touch_the_other(client, db, make_token):
    user_a, user_b = uuid.uuid4(), uuid.uuid4()
    token_a = make_token(user_a, email="a@example.com")
    token_b = make_token(user_b, email="b@example.com")
    client.get("/api/v1/me", headers=auth_header(token_a))
    client.get("/api/v1/me", headers=auth_header(token_b))

    client.patch(
        "/api/v1/me", headers=auth_header(token_a), json={"full_name": "User A"}
    )

    profile_b = db.get(Profile, user_b)
    assert profile_b.full_name is None


def test_client_supplied_user_id_has_no_effect(client, make_token):
    """Identity comes only from the verified token, never from the request."""
    user_a, user_b = uuid.uuid4(), uuid.uuid4()
    token_a = make_token(user_a, email="a@example.com")
    client.get("/api/v1/me", headers=auth_header(token_a))

    # A malicious caller tries to act as user B via query string and body.
    response = client.get(
        f"/api/v1/me?user_id={user_b}", headers=auth_header(token_a)
    )
    updated = client.patch(
        "/api/v1/me",
        headers=auth_header(token_a),
        json={"full_name": "Sneaky", "user_id": str(user_b)},
    )

    assert response.json()["data"]["id"] == str(user_a)
    # Unknown fields in the body are ignored, not applied as identity.
    assert updated.json()["data"]["id"] == str(user_a)


def test_preferences_are_isolated(client, db, make_token):
    user_a, user_b = uuid.uuid4(), uuid.uuid4()
    token_a = make_token(user_a, email="a@example.com")
    token_b = make_token(user_b, email="b@example.com")
    client.get("/api/v1/me", headers=auth_header(token_a))
    client.get("/api/v1/me", headers=auth_header(token_b))

    client.patch(
        "/api/v1/me/preferences", headers=auth_header(token_a), json={"currency_code": "USD"}
    )

    prefs_b = db.scalar(select(UserPreferences).where(UserPreferences.user_id == user_b))
    assert prefs_b.currency_code == "NGN"


def test_unauthenticated_calls_cannot_reach_data(client):
    assert client.get("/api/v1/me").status_code == 401
    assert client.get("/api/v1/me/preferences").status_code == 401
    assert client.patch("/api/v1/me", json={"full_name": "x"}).status_code == 401
