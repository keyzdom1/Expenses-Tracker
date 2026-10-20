"""Phase 6: recurring bills, the daily job, notifications and CSV export."""

import csv
import io
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.config import get_settings

TZ = "Africa/Lagos"


def today() -> date:
    return datetime.now(ZoneInfo(TZ)).date()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def setup_user(client, make_token, email: str = "a@example.com"):
    token = make_token(email=email)
    headers = auth(token)
    assert client.get("/api/v1/me", headers=headers).status_code == 200
    return token, headers


def make_account(client, headers, name="Cash", opening=0):
    response = client.post(
        "/api/v1/accounts",
        headers=headers,
        json={"name": name, "type": "cash", "opening_balance_minor": opening},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def category(client, headers, kind="expense", name=None):
    rows = client.get("/api/v1/categories", headers=headers).json()["data"]
    for row in rows:
        if row["kind"] == kind and (name is None or row["name"] == name):
            return row
    raise AssertionError("category not found")


def make_recurring(client, headers, account_id, **overrides):
    payload = {
        "type": "expense",
        "amount_minor": 2_500,
        "account_id": account_id,
        "vendor": "Netflix",
        "frequency": "monthly",
        "interval_count": 1,
        "start_date": today().isoformat(),
        "reminder_days": 3,
    }
    payload.update(overrides)
    response = client.post("/api/v1/recurring", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()["data"]


def run_job(client, headers=None, secret=None):
    request_headers = dict(headers or {})
    if secret:
        request_headers["X-Cron-Secret"] = secret
    return client.post("/api/v1/jobs/run", headers=request_headers)


def make_tx(client, headers, account_id, **overrides):
    payload = {
        "type": "expense",
        "amount_minor": 1_000,
        "account_id": account_id,
        "transaction_date": today().isoformat(),
    }
    payload.update(overrides)
    response = client.post("/api/v1/transactions", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()["data"]


def test_recurring_crud_and_deactivation(client, make_token):
    _, headers = setup_user(client, make_token)
    account = make_account(client, headers)

    recurring = make_recurring(client, headers, account["id"])
    assert recurring["frequency"] == "monthly"
    assert recurring["next_occurrence"] == today().isoformat()
    assert recurring["is_active"] is True
    assert recurring["account"]["name"] == "Cash"

    listed = client.get("/api/v1/recurring", headers=headers).json()["data"]
    assert len(listed) == 1

    updated = client.patch(
        f"/api/v1/recurring/{recurring['id']}",
        headers=headers,
        json={"amount_minor": 4_000, "vendor": "Netflix Premium"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["data"]["amount_minor"] == 4_000
    assert updated.json()["data"]["vendor"] == "Netflix Premium"

    paused = client.delete(f"/api/v1/recurring/{recurring['id']}", headers=headers)
    assert paused.status_code == 200
    assert paused.json()["data"]["is_active"] is False

    assert client.get("/api/v1/recurring", headers=headers).json()["data"] == []
    with_inactive = client.get(
        "/api/v1/recurring", headers=headers, params={"include_inactive": True}
    ).json()["data"]
    assert len(with_inactive) == 1


def test_recurring_rejects_an_end_date_before_the_start(client, make_token):
    _, headers = setup_user(client, make_token)
    account = make_account(client, headers)

    response = client.post(
        "/api/v1/recurring",
        headers=headers,
        json={
            "type": "expense",
            "amount_minor": 1_000,
            "account_id": account["id"],
            "frequency": "monthly",
            "start_date": today().isoformat(),
            "end_date": (today() - timedelta(days=1)).isoformat(),
        },
    )

    assert response.status_code == 422


def test_job_generates_bills_idempotently(client, make_token):
    _, headers = setup_user(client, make_token)
    account = make_account(client, headers)
    make_recurring(client, headers, account["id"])

    first = run_job(client, headers)
    assert first.status_code == 200, first.text
    assert first.json()["data"]["bills_created"] == 1

    second = run_job(client, headers)
    assert second.json()["data"]["bills_created"] == 0

    bills = client.get("/api/v1/bills", headers=headers).json()["data"]
    assert len(bills) == 1
    assert bills[0]["due_date"] == today().isoformat()
    assert bills[0]["status"] == "pending"
    assert bills[0]["vendor"] == "Netflix"
    assert bills[0]["type"] == "expense"


def test_job_marks_past_bills_overdue(client, make_token):
    _, headers = setup_user(client, make_token)
    account = make_account(client, headers)
    recurring = make_recurring(
        client,
        headers,
        account["id"],
        start_date=(today() - timedelta(days=10)).isoformat(),
        frequency="yearly",
    )
    assert recurring["is_active"] is True

    run_job(client, headers)
    bills = client.get("/api/v1/bills", headers=headers).json()["data"]

    assert len(bills) == 1
    assert bills[0]["status"] == "overdue"


def test_paying_a_bill_creates_a_matching_transaction(client, make_token):
    _, headers = setup_user(client, make_token)
    account = make_account(client, headers, opening=10_000)
    food = category(client, headers, name="Food & groceries")
    make_recurring(client, headers, account["id"], category_id=food["id"], amount_minor=2_500)
    run_job(client, headers)

    bill = client.get("/api/v1/bills", headers=headers).json()["data"][0]
    paid = client.post(f"/api/v1/bills/{bill['id']}/pay", headers=headers)
    assert paid.status_code == 200, paid.text
    paid_bill = paid.json()["data"]

    assert paid_bill["status"] == "paid"
    assert paid_bill["paid_transaction_id"]

    transaction = client.get(
        f"/api/v1/transactions/{paid_bill['paid_transaction_id']}", headers=headers
    ).json()["data"]
    assert transaction["type"] == "expense"
    assert transaction["amount_minor"] == 2_500
    assert transaction["transaction_date"] == bill["due_date"]
    assert transaction["vendor"] == "Netflix"

    accounts = client.get("/api/v1/accounts", headers=headers).json()["data"]
    cash = next(row for row in accounts if row["name"] == "Cash")
    assert cash["balance_minor"] == 7_500

    again = client.post(f"/api/v1/bills/{bill['id']}/pay", headers=headers)
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "bill_already_settled"


def test_paying_a_transfer_bill_moves_money_between_accounts(client, make_token):
    _, headers = setup_user(client, make_token)
    cash = make_account(client, headers, name="Cash", opening=50_000)
    savings = make_account(client, headers, name="Savings")
    make_recurring(
        client,
        headers,
        cash["id"],
        type="transfer",
        dest_account_id=savings["id"],
        amount_minor=15_000,
        vendor=None,
        description="Monthly savings",
    )
    run_job(client, headers)

    bill = client.get("/api/v1/bills", headers=headers).json()["data"][0]
    assert client.post(f"/api/v1/bills/{bill['id']}/pay", headers=headers).status_code == 200

    accounts = {
        row["name"]: row["balance_minor"]
        for row in client.get("/api/v1/accounts", headers=headers).json()["data"]
    }
    assert accounts["Cash"] == 35_000
    assert accounts["Savings"] == 15_000

    overview = client.get("/api/v1/reports/overview", headers=headers).json()["data"]
    assert overview["totals"]["expenses_minor"] == 0
    assert overview["totals"]["income_minor"] == 0


def test_skipping_a_bill_creates_no_transaction(client, make_token):
    _, headers = setup_user(client, make_token)
    account = make_account(client, headers)
    make_recurring(client, headers, account["id"])
    run_job(client, headers)

    bill = client.get("/api/v1/bills", headers=headers).json()["data"][0]
    skipped = client.post(f"/api/v1/bills/{bill['id']}/skip", headers=headers)
    assert skipped.status_code == 200
    assert skipped.json()["data"]["status"] == "skipped"
    assert skipped.json()["data"]["paid_transaction_id"] is None

    assert client.get("/api/v1/transactions", headers=headers).json()["data"] == []
    assert (
        client.post(f"/api/v1/bills/{bill['id']}/skip", headers=headers).status_code == 409
    )


def test_bill_due_notifications_are_deduped_and_readable(client, make_token):
    _, headers = setup_user(client, make_token)
    account = make_account(client, headers)
    make_recurring(client, headers, account["id"])
    run_job(client, headers)

    listed = client.get("/api/v1/notifications", headers=headers)
    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert body["meta"]["unread_count"] == 1
    assert len(body["data"]) == 1
    assert body["data"][0]["type"] == "bill_due"
    assert body["data"][0]["read_at"] is None

    run_job(client, headers)
    assert len(client.get("/api/v1/notifications", headers=headers).json()["data"]) == 1

    notification_id = body["data"][0]["id"]
    read = client.post(f"/api/v1/notifications/{notification_id}/read", headers=headers)
    assert read.status_code == 200
    assert read.json()["data"]["read_at"] is not None

    assert (
        client.get("/api/v1/notifications", headers=headers).json()["meta"]["unread_count"] == 0
    )
    assert (
        len(
            client.get(
                "/api/v1/notifications", headers=headers, params={"unread_only": True}
            ).json()["data"]
        )
        == 0
    )


def test_budget_threshold_notifications(client, make_token):
    _, headers = setup_user(client, make_token)
    account = make_account(client, headers)

    created = client.post(
        "/api/v1/budgets",
        headers=headers,
        json={"name": "All spending", "amount_minor": 100_000, "period": "monthly"},
    )
    assert created.status_code == 201, created.text
    make_tx(client, headers, account["id"], amount_minor=95_000)

    run_job(client, headers)
    notifications = client.get("/api/v1/notifications", headers=headers).json()["data"]
    budget_alerts = [row for row in notifications if row["type"] == "budget_threshold"]
    assert len(budget_alerts) == 1
    assert budget_alerts[0]["payload"]["state"] == "critical"

    run_job(client, headers)
    notifications = client.get("/api/v1/notifications", headers=headers).json()["data"]
    assert len([row for row in notifications if row["type"] == "budget_threshold"]) == 1

    marked = client.post("/api/v1/notifications/read-all", headers=headers)
    assert marked.status_code == 200
    assert marked.json()["data"]["updated"] == 1
    assert (
        client.get("/api/v1/notifications", headers=headers).json()["meta"]["unread_count"] == 0
    )


def test_notification_preferences_suppress_alerts(client, make_token):
    _, headers = setup_user(client, make_token)
    account = make_account(client, headers)
    make_recurring(client, headers, account["id"])
    client.post(
        "/api/v1/budgets",
        headers=headers,
        json={"name": "All spending", "amount_minor": 10_000, "period": "monthly"},
    )
    make_tx(client, headers, account["id"], amount_minor=9_500)

    patched = client.patch(
        "/api/v1/me/preferences",
        headers=headers,
        json={"notify_upcoming_bills": False, "notify_budget_thresholds": False},
    )
    assert patched.status_code == 200, patched.text

    run_job(client, headers)
    assert client.get("/api/v1/notifications", headers=headers).json()["data"] == []
    assert len(client.get("/api/v1/bills", headers=headers).json()["data"]) == 1

    client.patch(
        "/api/v1/me/preferences",
        headers=headers,
        json={"notify_upcoming_bills": True, "notify_budget_thresholds": True},
    )
    run_job(client, headers)

    types = {
        row["type"]
        for row in client.get("/api/v1/notifications", headers=headers).json()["data"]
    }
    assert types == {"bill_due", "budget_threshold"}


def test_job_requires_the_configured_secret(client, make_token, monkeypatch):
    monkeypatch.setattr(get_settings(), "cron_secret", "top-secret")

    assert run_job(client).status_code == 401
    assert run_job(client, secret="wrong").status_code == 401

    allowed = run_job(client, secret="top-secret")
    assert allowed.status_code == 200, allowed.text


def test_on_demand_job_is_scoped_to_the_signed_in_user(client, make_token):
    _, headers_a = setup_user(client, make_token, "a@example.com")
    _, headers_b = setup_user(client, make_token, "b@example.com")
    account = make_account(client, headers_a)
    make_recurring(client, headers_a, account["id"])

    response = client.post("/api/v1/jobs/run/me", headers=headers_a)
    assert response.status_code == 200, response.text
    assert response.json()["data"]["bills_created"] == 1

    assert len(client.get("/api/v1/bills", headers=headers_a).json()["data"]) == 1
    assert client.get("/api/v1/bills", headers=headers_b).json()["data"] == []

    # Bills generated by the background job are visible to the same user.
    account_b = make_account(client, headers_b, name="B Wallet")
    make_recurring(client, headers_b, account_b["id"])
    run_job(client)
    assert len(client.get("/api/v1/bills", headers=headers_b).json()["data"]) == 1


def test_recurring_and_bills_are_isolated_between_users(client, make_token):
    _, headers_a = setup_user(client, make_token, "a@example.com")
    _, headers_b = setup_user(client, make_token, "b@example.com")
    account = make_account(client, headers_a)
    recurring = make_recurring(client, headers_a, account["id"])
    run_job(client, headers_a)
    bill = client.get("/api/v1/bills", headers=headers_a).json()["data"][0]

    assert client.get("/api/v1/recurring", headers=headers_b).json()["data"] == []
    assert client.get("/api/v1/bills", headers=headers_b).json()["data"] == []
    assert client.get("/api/v1/notifications", headers=headers_b).json()["data"] == []

    assert (
        client.patch(
            f"/api/v1/recurring/{recurring['id']}",
            headers=headers_b,
            json={"amount_minor": 1},
        ).status_code
        == 404
    )
    assert (
        client.post(f"/api/v1/bills/{bill['id']}/pay", headers=headers_b).status_code == 404
    )
    assert (
        client.post(f"/api/v1/bills/{bill['id']}/skip", headers=headers_b).status_code == 404
    )


def test_csv_export_contains_the_period_transactions(client, make_token):
    _, headers = setup_user(client, make_token)
    account = make_account(client, headers)
    other = make_account(client, headers, name="Savings")
    food = category(client, headers, name="Food & groceries")

    make_tx(
        client,
        headers,
        account["id"],
        amount_minor=1_234,
        vendor="Corner Shop",
        description="Lunch, with commas",
        category_id=food["id"],
    )
    make_tx(
        client,
        headers,
        account["id"],
        type="transfer",
        amount_minor=5_000,
        dest_account_id=other["id"],
        transaction_date=(today() - timedelta(days=1)).isoformat(),
    )

    response = client.get(
        "/api/v1/reports/transactions.csv",
        headers=headers,
        params={
            "date_from": (today() - timedelta(days=7)).isoformat(),
            "date_to": today().isoformat(),
        },
    )

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]

    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows[0][:4] == ["Date", "Type", "Amount", "Currency"]
    assert len(rows) == 3

    by_type = {row[1]: row for row in rows[1:]}
    assert by_type["expense"][2] == "12.34"
    assert by_type["expense"][3] == "NGN"
    assert by_type["expense"][4] == "Corner Shop"
    assert by_type["expense"][5] == "Lunch, with commas"
    assert by_type["expense"][6] == "Food & groceries"
    assert by_type["transfer"][8] == "Savings"


def test_csv_export_is_empty_for_a_new_user(client, make_token):
    _, headers = setup_user(client, make_token)

    response = client.get("/api/v1/reports/transactions.csv", headers=headers)

    assert response.status_code == 200
    rows = list(csv.reader(io.StringIO(response.text)))
    assert len(rows) == 1
