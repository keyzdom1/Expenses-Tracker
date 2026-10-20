"""Phase 7: hardening, rate limiting and export limits."""

from datetime import date, timedelta

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.main import app


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_security_headers_and_request_id_are_present(client):
    response = client.get("/health", headers={"X-Request-ID": "phase7-check"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "phase7-check"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "camera=()" in response.headers["Permissions-Policy"]


def test_rate_limit_returns_the_standard_error_envelope(client):
    original = app.state.limiter
    app.state.limiter = Limiter(key_func=get_remote_address, default_limits=["2/minute"])

    try:
        assert client.get("/").status_code == 200
        assert client.get("/").status_code == 200

        limited = client.get("/")
        assert limited.status_code == 429
        error = limited.json()["error"]
        assert error["code"] == "rate_limited"
        assert "Too many requests" in error["message"]
        assert "limit" in error["details"]
    finally:
        app.state.limiter = original


def test_csv_export_rejects_a_range_over_two_years(client, user_token):
    headers = auth(user_token)
    assert client.get("/api/v1/me", headers=headers).status_code == 200

    start = date(2023, 1, 1)
    end = start + timedelta(days=800)
    response = client.get(
        "/api/v1/reports/transactions.csv",
        headers=headers,
        params={"date_from": start.isoformat(), "date_to": end.isoformat()},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "date_range_too_large"


def test_data_export_contains_owned_rows(client, user_token, make_token):
    headers = auth(user_token)
    profile = client.get("/api/v1/me", headers=headers).json()["data"]
    account = client.post(
        "/api/v1/accounts",
        headers=headers,
        json={"name": "Cash", "type": "cash", "opening_balance_minor": 10_000},
    ).json()["data"]
    client.post(
        "/api/v1/transactions",
        headers=headers,
        json={
            "type": "expense",
            "amount_minor": 1_500,
            "account_id": account["id"],
            "transaction_date": date.today().isoformat(),
            "vendor": "Market",
        },
    )
    client.post(
        "/api/v1/budgets",
        headers=headers,
        json={"name": "Food", "amount_minor": 20_000, "period": "monthly"},
    )

    other_headers = auth(make_token(email="other@example.com"))
    client.get("/api/v1/me", headers=other_headers)
    client.post(
        "/api/v1/accounts",
        headers=other_headers,
        json={"name": "Other wallet", "type": "cash"},
    )

    response = client.get("/api/v1/me/export", headers=headers)

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/json")
    assert "attachment" in response.headers["content-disposition"]
    assert response.headers["content-disposition"].endswith('.json"')

    payload = response.json()
    assert payload["profile"]["id"] == profile["id"]
    assert payload["format_version"] == 1
    assert len(payload["tables"]["accounts"]) == 1
    assert len(payload["tables"]["transactions"]) == 1
    assert len(payload["tables"]["budgets"]) == 1
    assert payload["tables"]["transactions"][0]["vendor"] == "Market"
    assert "audit_logs" in payload["tables"]
    assert all(row["name"] != "Other wallet" for row in payload["tables"]["accounts"])


def test_account_deletion_requires_typed_confirmation_and_removes_data(
    client, make_token
):
    token = make_token(email="delete-me@example.com")
    headers = auth(token)
    client.get("/api/v1/me", headers=headers)
    client.post(
        "/api/v1/accounts",
        headers=headers,
        json={"name": "Cash", "type": "cash"},
    )

    refused = client.request(
        "DELETE", "/api/v1/me", headers=headers, json={"confirm": "delete"}
    )
    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "confirmation_required"
    assert len(client.get("/api/v1/accounts", headers=headers).json()["data"]) == 1

    deleted = client.request(
        "DELETE", "/api/v1/me", headers=headers, json={"confirm": "DELETE"}
    )
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["data"]["deleted"] is True
    assert deleted.json()["data"]["auth_user_deleted"] is False

    # The token is still valid locally; the first request recreates an empty profile.
    assert client.get("/api/v1/accounts", headers=headers).json()["data"] == []
    assert client.get("/api/v1/me", headers=headers).json()["data"]["email"] == (
        "delete-me@example.com"
    )
