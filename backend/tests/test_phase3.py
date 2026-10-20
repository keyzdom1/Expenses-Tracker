"""Phase 3: categories, accounts, transactions, balances and isolation."""

import uuid
from datetime import date, timedelta


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def setup_user(client, make_token, email: str = "a@example.com"):
    token = make_token(email=email)
    headers = auth(token)
    assert client.get("/api/v1/me", headers=headers).status_code == 200
    return token, headers


def make_account(client, headers, name="Cash", type_="cash", currency=None, opening=0):
    payload = {"name": name, "type": type_, "opening_balance_minor": opening}
    if currency:
        payload["currency_code"] = currency
    response = client.post("/api/v1/accounts", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()["data"]


def categories(client, headers):
    return client.get("/api/v1/categories", headers=headers).json()["data"]


def pick_category(client, headers, kind="expense", name=None):
    rows = categories(client, headers)
    for row in rows:
        if row["kind"] != kind:
            continue
        if name is None or row["name"] == name:
            return row
    raise AssertionError(f"No {kind} category found")


def make_tx(client, headers, account_id, **overrides):
    payload = {
        "type": "expense",
        "amount_minor": 1000,
        "account_id": account_id,
        "transaction_date": date.today().isoformat(),
    }
    payload.update(overrides)
    return client.post("/api/v1/transactions", headers=headers, json=payload)


def account_balance(client, headers, account_id):
    response = client.get(f"/api/v1/accounts/{account_id}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["data"]["balance_minor"]


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------


def test_first_access_seeds_default_categories(client, make_token):
    _, headers = setup_user(client, make_token)

    rows = categories(client, headers)

    expense = [row for row in rows if row["kind"] == "expense"]
    income = [row for row in rows if row["kind"] == "income"]
    assert len(expense) == 15
    assert len(income) == 6
    assert any(row["name"] == "Salary" for row in income)


def test_defaults_are_only_seeded_once(client, make_token):
    _, headers = setup_user(client, make_token)

    categories(client, headers)
    second = categories(client, headers)

    assert len(second) == 21


def test_custom_category_and_subcategory(client, make_token):
    _, headers = setup_user(client, make_token)
    parent = pick_category(client, headers, "expense", "Food & groceries")

    response = client.post(
        "/api/v1/categories",
        headers=headers,
        json={"name": "Groceries", "kind": "expense", "parent_id": parent["id"]},
    )

    assert response.status_code == 201
    assert response.json()["data"]["parent_id"] == parent["id"]


def test_duplicate_category_is_rejected(client, make_token):
    _, headers = setup_user(client, make_token)

    response = client.post(
        "/api/v1/categories", headers=headers, json={"name": "Salary", "kind": "income"}
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "duplicate_category"


def test_category_used_by_a_transaction_cannot_be_deleted(client, make_token):
    _, headers = setup_user(client, make_token)
    account = make_account(client, headers)
    category = pick_category(client, headers)
    make_tx(client, headers, account["id"], category_id=category["id"])

    response = client.delete(f"/api/v1/categories/{category['id']}", headers=headers)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "category_in_use"


# ---------------------------------------------------------------------------
# Accounts and balances
# ---------------------------------------------------------------------------


def test_account_creation_and_opening_balance(client, make_token):
    _, headers = setup_user(client, make_token)

    account = make_account(client, headers, name="GTBank", type_="bank", opening=50_000)

    assert account["name"] == "GTBank"
    assert account["currency_code"] == "NGN"
    assert account["balance_minor"] == 50_000


def test_balances_follow_income_expense_and_refund(client, make_token):
    _, headers = setup_user(client, make_token)
    account = make_account(client, headers, opening=100_000)
    category = pick_category(client, headers)

    assert make_tx(client, headers, account["id"], amount_minor=25_000, category_id=category["id"]).status_code == 201
    assert account_balance(client, headers, account["id"]) == 75_000

    assert make_tx(
        client,
        headers,
        account["id"],
        type="income",
        amount_minor=50_000,
        category_id=pick_category(client, headers, "income")["id"],
    ).status_code == 201
    assert account_balance(client, headers, account["id"]) == 125_000

    assert make_tx(
        client,
        headers,
        account["id"],
        type="refund",
        amount_minor=5_000,
        category_id=category["id"],
    ).status_code == 201
    assert account_balance(client, headers, account["id"]) == 130_000


def test_transfer_moves_money_and_is_excluded_from_totals(client, make_token):
    _, headers = setup_user(client, make_token)
    cash = make_account(client, headers, name="Cash", opening=100_000)
    bank = make_account(client, headers, name="Bank", type_="bank")

    response = make_tx(
        client,
        headers,
        cash["id"],
        type="transfer",
        amount_minor=20_000,
        dest_account_id=bank["id"],
    )

    assert response.status_code == 201
    assert account_balance(client, headers, cash["id"]) == 80_000
    assert account_balance(client, headers, bank["id"]) == 20_000

    totals = client.get("/api/v1/transactions", headers=headers).json()["meta"]["totals"]
    assert totals == []


def test_totals_reconcile_with_transactions(client, make_token):
    _, headers = setup_user(client, make_token)
    account = make_account(client, headers)
    expense_category = pick_category(client, headers)
    income_category = pick_category(client, headers, "income")

    make_tx(client, headers, account["id"], amount_minor=25_000, category_id=expense_category["id"])
    make_tx(
        client,
        headers,
        account["id"],
        type="income",
        amount_minor=80_000,
        category_id=income_category["id"],
    )
    make_tx(
        client,
        headers,
        account["id"],
        type="refund",
        amount_minor=5_000,
        category_id=expense_category["id"],
    )

    body = client.get("/api/v1/transactions", headers=headers).json()
    totals = body["meta"]["totals"][0]

    assert totals["currency_code"] == "NGN"
    assert totals["income_minor"] == 80_000
    assert totals["expenses_minor"] == 25_000
    assert totals["refunds_minor"] == 5_000
    assert totals["spending_minor"] == 20_000
    assert totals["net_minor"] == 60_000
    assert totals["transaction_count"] == 3
    assert body["meta"]["total"] == 3


def test_archived_account_rejects_new_transactions(client, make_token):
    _, headers = setup_user(client, make_token)
    account = make_account(client, headers)

    archived = client.delete(f"/api/v1/accounts/{account['id']}", headers=headers)

    assert archived.status_code == 200
    assert archived.json()["data"]["is_active"] is False

    response = make_tx(client, headers, account["id"])
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "account_archived"

    listed = client.get("/api/v1/accounts", headers=headers).json()["data"]
    assert listed == []


# ---------------------------------------------------------------------------
# Transaction validation
# ---------------------------------------------------------------------------


def test_zero_amount_is_rejected(client, make_token):
    _, headers = setup_user(client, make_token)
    account = make_account(client, headers)

    response = make_tx(client, headers, account["id"], amount_minor=0)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_transfer_requires_a_destination(client, make_token):
    _, headers = setup_user(client, make_token)
    account = make_account(client, headers)

    response = make_tx(client, headers, account["id"], type="transfer", amount_minor=1000)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "transfer_destination_required"


def test_cross_currency_transfer_is_rejected(client, make_token):
    _, headers = setup_user(client, make_token)
    naira = make_account(client, headers, name="Naira")
    dollars = make_account(client, headers, name="Dollars", currency="USD")

    response = make_tx(
        client,
        headers,
        naira["id"],
        type="transfer",
        amount_minor=1000,
        dest_account_id=dollars["id"],
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "currency_mismatch"


def test_expense_cannot_use_an_income_category(client, make_token):
    _, headers = setup_user(client, make_token)
    account = make_account(client, headers)
    income_category = pick_category(client, headers, "income")

    response = make_tx(client, headers, account["id"], category_id=income_category["id"])

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "category_kind_mismatch"


# ---------------------------------------------------------------------------
# Idempotency, filters, deletion
# ---------------------------------------------------------------------------


def test_idempotency_key_returns_the_original_transaction(client, make_token):
    _, headers = setup_user(client, make_token)
    account = make_account(client, headers)
    key = str(uuid.uuid4())
    payload = {
        "type": "expense",
        "amount_minor": 4200,
        "account_id": account["id"],
        "transaction_date": date.today().isoformat(),
    }

    first = client.post(
        "/api/v1/transactions", headers={**headers, "Idempotency-Key": key}, json=payload
    )
    second = client.post(
        "/api/v1/transactions", headers={**headers, "Idempotency-Key": key}, json=payload
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["data"]["id"] == second.json()["data"]["id"]
    assert client.get("/api/v1/transactions", headers=headers).json()["meta"]["total"] == 1


def test_reusing_a_key_with_a_different_body_conflicts(client, make_token):
    _, headers = setup_user(client, make_token)
    account = make_account(client, headers)
    key = str(uuid.uuid4())
    payload = {
        "type": "expense",
        "amount_minor": 4200,
        "account_id": account["id"],
        "transaction_date": date.today().isoformat(),
    }

    client.post("/api/v1/transactions", headers={**headers, "Idempotency-Key": key}, json=payload)
    response = client.post(
        "/api/v1/transactions",
        headers={**headers, "Idempotency-Key": key},
        json={**payload, "amount_minor": 9900},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "idempotency_conflict"


def test_filters_search_and_pagination(client, make_token):
    _, headers = setup_user(client, make_token)
    account = make_account(client, headers)

    make_tx(client, headers, account["id"], vendor="Shoprite", amount_minor=1000)
    make_tx(client, headers, account["id"], vendor="Uber", amount_minor=2000)
    make_tx(client, headers, account["id"], vendor="Uber Eats", amount_minor=3000)

    search = client.get("/api/v1/transactions?search=uber", headers=headers).json()
    assert search["meta"]["total"] == 2

    page = client.get("/api/v1/transactions?page_size=2&page=2", headers=headers).json()
    assert len(page["data"]) == 1
    assert page["meta"]["total_pages"] == 2

    dated = client.get(
        f"/api/v1/transactions?date_from={(date.today() - timedelta(days=1)).isoformat()}",
        headers=headers,
    ).json()
    assert dated["meta"]["total"] == 3

    future = client.get(
        f"/api/v1/transactions?date_from={(date.today() + timedelta(days=1)).isoformat()}",
        headers=headers,
    ).json()
    assert future["meta"]["total"] == 0


def test_soft_delete_hides_the_transaction_and_restores_the_balance(client, make_token):
    _, headers = setup_user(client, make_token)
    account = make_account(client, headers, opening=10_000)
    created = make_tx(client, headers, account["id"], amount_minor=4_000).json()["data"]

    assert account_balance(client, headers, account["id"]) == 6_000

    deleted = client.delete(f"/api/v1/transactions/{created['id']}", headers=headers)
    assert deleted.status_code == 200

    assert client.get(f"/api/v1/transactions/{created['id']}", headers=headers).status_code == 404
    assert account_balance(client, headers, account["id"]) == 10_000


# ---------------------------------------------------------------------------
# Isolation
# ---------------------------------------------------------------------------


def test_user_b_cannot_touch_user_a_records(client, make_token):
    _, headers_a = setup_user(client, make_token, "a@example.com")
    _, headers_b = setup_user(client, make_token, "b@example.com")

    account_a = make_account(client, headers_a)
    category_a = pick_category(client, headers_a)
    tx_a = make_tx(client, headers_a, account_a["id"], category_id=category_a["id"]).json()["data"]

    assert client.get(f"/api/v1/transactions/{tx_a['id']}", headers=headers_b).status_code == 404
    assert client.patch(
        f"/api/v1/transactions/{tx_a['id']}", headers=headers_b, json={"amount_minor": 1}
    ).status_code == 404
    assert client.delete(
        f"/api/v1/transactions/{tx_a['id']}", headers=headers_b
    ).status_code == 404

    assert client.get(f"/api/v1/accounts/{account_a['id']}", headers=headers_b).status_code == 404
    assert client.patch(
        f"/api/v1/accounts/{account_a['id']}", headers=headers_b, json={"name": "Hacked"}
    ).status_code == 404
    assert client.delete(
        f"/api/v1/accounts/{account_a['id']}", headers=headers_b
    ).status_code == 404

    assert client.patch(
        f"/api/v1/categories/{category_a['id']}", headers=headers_b, json={"name": "Hacked"}
    ).status_code == 404
    assert client.delete(
        f"/api/v1/categories/{category_a['id']}", headers=headers_b
    ).status_code == 404

    assert client.get("/api/v1/transactions", headers=headers_b).json()["meta"]["total"] == 0
    assert client.get("/api/v1/accounts", headers=headers_b).json()["data"] == []


def test_cannot_post_a_transaction_into_another_users_account(client, make_token):
    _, headers_a = setup_user(client, make_token, "a@example.com")
    _, headers_b = setup_user(client, make_token, "b@example.com")
    account_a = make_account(client, headers_a)

    response = make_tx(client, headers_b, account_a["id"])

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
