"""Phase 4: authoritative dashboard totals and budgets."""

import calendar
from datetime import date, timedelta


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def setup_user(client, make_token, email: str = "a@example.com"):
    token = make_token(email=email)
    headers = auth(token)
    assert client.get("/api/v1/me", headers=headers).status_code == 200
    return token, headers


def make_account(client, headers, name="Cash", opening=0, currency=None):
    payload = {"name": name, "type": "cash", "opening_balance_minor": opening}
    if currency:
        payload["currency_code"] = currency
    response = client.post("/api/v1/accounts", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()["data"]


def category(client, headers, kind="expense", name=None):
    rows = client.get("/api/v1/categories", headers=headers).json()["data"]
    for row in rows:
        if row["kind"] == kind and (name is None or row["name"] == name):
            return row
    raise AssertionError("category not found")


def make_tx(client, headers, account_id, **overrides):
    payload = {
        "type": "expense",
        "amount_minor": 1000,
        "account_id": account_id,
        "transaction_date": date.today().isoformat(),
    }
    payload.update(overrides)
    response = client.post("/api/v1/transactions", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()["data"]


def overview(client, headers, **params):
    return client.get("/api/v1/reports/overview", headers=headers, params=params)


def test_overview_reconciles_with_transactions(client, make_token):
    _, headers = setup_user(client, make_token)
    account = make_account(client, headers, opening=10_000)
    other = make_account(client, headers, name="Savings")
    food = category(client, headers, name="Food & groceries")
    salary = category(client, headers, "income", "Salary")

    make_tx(client, headers, account["id"], amount_minor=30_000, category_id=food["id"])
    make_tx(
        client,
        headers,
        account["id"],
        type="income",
        amount_minor=100_000,
        category_id=salary["id"],
    )
    make_tx(
        client,
        headers,
        account["id"],
        type="refund",
        amount_minor=5_000,
        category_id=food["id"],
    )
    make_tx(
        client,
        headers,
        account["id"],
        type="transfer",
        amount_minor=10_000,
        dest_account_id=other["id"],
    )

    body = overview(client, headers).json()["data"]
    totals = body["totals"]

    assert body["currency_code"] == "NGN"
    assert totals["income_minor"] == 100_000
    assert totals["expenses_minor"] == 30_000
    assert totals["refunds_minor"] == 5_000
    assert totals["spending_minor"] == 25_000
    assert totals["net_minor"] == 75_000
    assert totals["savings_rate"] == 75.0
    assert totals["transaction_count"] == 3  # transfer excluded

    assert len(body["by_category"]) == 1
    slice_ = body["by_category"][0]
    assert slice_["name"] == "Food & groceries"
    assert slice_["spent_minor"] == 25_000
    assert slice_["share"] == 100.0

    accounts = {row["name"]: row["balance_minor"] for row in body["accounts"]}
    assert accounts["Cash"] == 10_000 + 100_000 - 30_000 + 5_000 - 10_000
    assert accounts["Savings"] == 10_000

    assert len(body["recent"]) == 4
    assert [point["period"] for point in body["trend"]][-1] == date.today().strftime("%Y-%m")


def test_overview_defaults_to_the_current_month(client, make_token):
    _, headers = setup_user(client, make_token)
    account = make_account(client, headers)

    today = date.today()
    last_month_end = today.replace(day=1) - timedelta(days=1)
    make_tx(
        client,
        headers,
        account["id"],
        amount_minor=777,
        transaction_date=last_month_end.isoformat(),
    )
    make_tx(client, headers, account["id"], amount_minor=111)

    body = overview(client, headers).json()["data"]
    assert body["totals"]["expenses_minor"] == 111

    ranged = overview(
        client,
        headers,
        date_from=last_month_end.isoformat(),
        date_to=today.isoformat(),
    ).json()["data"]
    assert ranged["totals"]["expenses_minor"] == 888


def test_overview_rejects_an_inverted_range(client, make_token):
    _, headers = setup_user(client, make_token)

    response = overview(
        client,
        headers,
        date_from=date.today().isoformat(),
        date_to=(date.today() - timedelta(days=1)).isoformat(),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_date_range"


def test_overview_is_empty_for_a_new_user(client, make_token):
    _, headers = setup_user(client, make_token)

    body = overview(client, headers).json()["data"]

    assert body["totals"]["income_minor"] == 0
    assert body["totals"]["spending_minor"] == 0
    assert body["totals"]["savings_rate"] is None
    assert body["by_category"] == []
    assert body["recent"] == []
    assert len(body["trend"]) == 6


def test_budget_actuals_and_thresholds(client, make_token):
    _, headers = setup_user(client, make_token)
    account = make_account(client, headers)
    food = category(client, headers, name="Food & groceries")

    created = client.post(
        "/api/v1/budgets",
        headers=headers,
        json={
            "name": "Food budget",
            "category_id": food["id"],
            "amount_minor": 10_000,
            "period": "monthly",
        },
    )
    assert created.status_code == 201, created.text
    budget = created.json()["data"]

    assert budget["currency_code"] == "NGN"
    assert budget["spent_minor"] == 0
    assert budget["state"] == "ok"

    make_tx(client, headers, account["id"], amount_minor=8_500, category_id=food["id"])
    listed = client.get("/api/v1/budgets", headers=headers).json()["data"][0]
    assert listed["spent_minor"] == 8_500
    assert listed["percent_used"] == 85.0
    assert listed["remaining_minor"] == 1_500
    assert listed["state"] == "warning"

    make_tx(client, headers, account["id"], amount_minor=1_000, category_id=food["id"])
    listed = client.get("/api/v1/budgets", headers=headers).json()["data"][0]
    assert listed["state"] == "critical"

    make_tx(client, headers, account["id"], amount_minor=1_500, category_id=food["id"])
    listed = client.get("/api/v1/budgets", headers=headers).json()["data"][0]
    assert listed["state"] == "exceeded"
    assert listed["remaining_minor"] == -1_000

    updated = client.patch(
        f"/api/v1/budgets/{budget['id']}",
        headers=headers,
        json={"amount_minor": 15_000},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["state"] == "ok"


def test_budget_excludes_refunds_and_transfers(client, make_token):
    _, headers = setup_user(client, make_token)
    account = make_account(client, headers)
    other = make_account(client, headers, name="Savings")
    food = category(client, headers, name="Food & groceries")

    client.post(
        "/api/v1/budgets",
        headers=headers,
        json={"name": "All spending", "amount_minor": 50_000, "period": "monthly"},
    )
    make_tx(client, headers, account["id"], amount_minor=20_000, category_id=food["id"])
    make_tx(client, headers, account["id"], type="refund", amount_minor=5_000, category_id=food["id"])
    make_tx(
        client,
        headers,
        account["id"],
        type="transfer",
        amount_minor=10_000,
        dest_account_id=other["id"],
    )

    listed = client.get("/api/v1/budgets", headers=headers).json()["data"][0]
    assert listed["spent_minor"] == 15_000


def test_custom_budget_requires_an_end_date(client, make_token):
    _, headers = setup_user(client, make_token)

    response = client.post(
        "/api/v1/budgets",
        headers=headers,
        json={"name": "Custom", "amount_minor": 10_000, "period": "custom"},
    )

    assert response.status_code == 422


def test_budget_rejects_an_income_category(client, make_token):
    _, headers = setup_user(client, make_token)
    salary = category(client, headers, "income", "Salary")

    response = client.post(
        "/api/v1/budgets",
        headers=headers,
        json={
            "name": "Salary budget",
            "category_id": salary["id"],
            "amount_minor": 10_000,
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "category_kind_mismatch"


def test_budgets_are_isolated_between_users(client, make_token):
    _, headers_a = setup_user(client, make_token, "a@example.com")
    _, headers_b = setup_user(client, make_token, "b@example.com")

    created = client.post(
        "/api/v1/budgets",
        headers=headers_a,
        json={"name": "Private", "amount_minor": 10_000},
    ).json()["data"]

    assert client.get("/api/v1/budgets", headers=headers_b).json()["data"] == []
    assert (
        client.patch(
            f"/api/v1/budgets/{created['id']}", headers=headers_b, json={"amount_minor": 1}
        ).status_code
        == 404
    )
    assert client.delete(f"/api/v1/budgets/{created['id']}", headers=headers_b).status_code == 404

    overview_b = overview(client, headers_b).json()["data"]
    assert overview_b["totals"]["spending_minor"] == 0
