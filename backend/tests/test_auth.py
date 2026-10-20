"""Authentication and profile/preferences tests."""

import uuid

from sqlalchemy import func, select

from app.models.profile import Profile, UserPreferences


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# --------------------------------------------------------------------------
# Token rejection
# --------------------------------------------------------------------------


def test_missing_token_is_rejected(client):
    response = client.get("/api/v1/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"


def test_malformed_token_is_rejected(client):
    response = client.get("/api/v1/me", headers=auth_header("not-a-jwt"))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"


def test_token_signed_with_wrong_secret_is_rejected(client, make_token):
    token = make_token(secret="attacker-secret-that-is-at-least-32-bytes")

    response = client.get("/api/v1/me", headers=auth_header(token))

    assert response.status_code == 401


def test_expired_token_is_rejected(client, make_token):
    token = make_token(expires_in=-60)

    response = client.get("/api/v1/me", headers=auth_header(token))

    assert response.status_code == 401


def test_wrong_audience_is_rejected(client, make_token):
    token = make_token(audience="some-other-app")

    response = client.get("/api/v1/me", headers=auth_header(token))

    assert response.status_code == 401


def test_token_without_expiry_is_rejected(client, make_token):
    token = make_token(include_exp=False)

    response = client.get("/api/v1/me", headers=auth_header(token))

    assert response.status_code == 401


def test_token_without_valid_subject_is_rejected(client, make_token):
    token = make_token(subject="not-a-uuid")

    response = client.get("/api/v1/me", headers=auth_header(token))

    assert response.status_code == 401


# --------------------------------------------------------------------------
# Profile bootstrap
# --------------------------------------------------------------------------


def test_first_request_creates_profile_and_default_preferences(client, db, make_token):
    user_id = uuid.uuid4()
    token = make_token(user_id, email="ada@example.com")

    response = client.get("/api/v1/me", headers=auth_header(token))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(user_id)
    assert data["email"] == "ada@example.com"

    assert db.scalar(select(func.count()).select_from(Profile)) == 1

    preferences = db.scalar(select(UserPreferences).where(UserPreferences.user_id == user_id))
    assert preferences is not None
    assert preferences.currency_code == "NGN"
    assert preferences.timezone == "Africa/Lagos"
    assert preferences.theme.value == "system"


def test_repeated_requests_do_not_duplicate_the_profile(client, db, make_token):
    token = make_token(email="ada@example.com")

    for _ in range(3):
        assert client.get("/api/v1/me", headers=auth_header(token)).status_code == 200

    assert db.scalar(select(func.count()).select_from(Profile)) == 1
    assert db.scalar(select(func.count()).select_from(UserPreferences)) == 1


def test_email_changes_are_synced_from_the_token(client, db, make_token):
    user_id = uuid.uuid4()

    first = make_token(user_id, email="old@example.com")
    client.get("/api/v1/me", headers=auth_header(first))

    second = make_token(user_id, email="new@example.com")
    response = client.get("/api/v1/me", headers=auth_header(second))

    assert response.json()["data"]["email"] == "new@example.com"
    assert db.get(Profile, user_id).email == "new@example.com"


def test_profile_can_be_updated(client, make_token):
    token = make_token(email="ada@example.com")
    client.get("/api/v1/me", headers=auth_header(token))

    response = client.patch(
        "/api/v1/me", headers=auth_header(token), json={"full_name": "Ada Lovelace"}
    )

    assert response.status_code == 200
    assert response.json()["data"]["full_name"] == "Ada Lovelace"


# --------------------------------------------------------------------------
# Preferences
# --------------------------------------------------------------------------


def test_preferences_can_be_updated(client, make_token):
    token = make_token(email="ada@example.com")
    client.get("/api/v1/me", headers=auth_header(token))

    response = client.patch(
        "/api/v1/me/preferences",
        headers=auth_header(token),
        json={"currency_code": "usd", "timezone": "Europe/London", "theme": "dark"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["currency_code"] == "USD"
    assert data["timezone"] == "Europe/London"
    assert data["theme"] == "dark"

    current = client.get("/api/v1/me/preferences", headers=auth_header(token))
    assert current.json()["data"]["theme"] == "dark"


def test_unknown_currency_is_rejected(client, make_token):
    token = make_token(email="ada@example.com")
    client.get("/api/v1/me", headers=auth_header(token))

    response = client.patch(
        "/api/v1/me/preferences", headers=auth_header(token), json={"currency_code": "XXX"}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "unknown_currency"


def test_invalid_timezone_is_rejected(client, make_token):
    token = make_token(email="ada@example.com")
    client.get("/api/v1/me", headers=auth_header(token))

    response = client.patch(
        "/api/v1/me/preferences",
        headers=auth_header(token),
        json={"timezone": "Mars/Olympus_Mons"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_preferences_work_as_the_very_first_request(client, db, make_token):
    """ThemeSync calls this in parallel with GET /me on a brand-new account."""
    user_id = uuid.uuid4()
    token = make_token(user_id, email="fresh@example.com")

    response = client.get("/api/v1/me/preferences", headers=auth_header(token))

    assert response.status_code == 200
    assert response.json()["data"]["currency_code"] == "NGN"
    assert db.get(Profile, user_id) is not None
    assert db.scalar(select(UserPreferences).where(UserPreferences.user_id == user_id)) is not None


def test_preference_update_works_as_the_very_first_request(client, make_token):
    token = make_token(email="fresh@example.com")

    response = client.patch(
        "/api/v1/me/preferences", headers=auth_header(token), json={"theme": "dark"}
    )

    assert response.status_code == 200
    assert response.json()["data"]["theme"] == "dark"
