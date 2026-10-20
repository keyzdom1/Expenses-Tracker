"""Phase 5: private receipts, signed URLs and ownership."""

from datetime import date
from urllib.parse import urlparse

from app.services import receipt_storage

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PDF_BYTES = b"%PDF-1.7\n" + b"0" * 64


def setup_user(client, make_token, email="a@example.com"):
    token = make_token(email=email)
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/v1/me", headers=headers).status_code == 200
    return headers


def make_transaction(client, headers):
    account = client.post(
        "/api/v1/accounts",
        headers=headers,
        json={"name": "Cash", "type": "cash", "opening_balance_minor": 0},
    ).json()["data"]
    return client.post(
        "/api/v1/transactions",
        headers=headers,
        json={
            "type": "expense",
            "amount_minor": 5000,
            "account_id": account["id"],
            "transaction_date": date.today().isoformat(),
        },
    ).json()["data"]


def upload(client, headers, transaction_id, content=PNG_BYTES, name="receipt.png", mime="image/png"):
    return client.post(
        f"/api/v1/transactions/{transaction_id}/receipt",
        headers=headers,
        files={"file": (name, content, mime)},
    )


def test_upload_metadata_and_signed_download(client, make_token):
    headers = setup_user(client, make_token)
    transaction = make_transaction(client, headers)

    response = upload(client, headers, transaction["id"])
    assert response.status_code == 201, response.text

    receipt = response.json()["data"]
    assert receipt["file_name"] == "receipt.png"
    assert receipt["mime_type"] == "image/png"
    assert receipt["size_bytes"] == len(PNG_BYTES)

    metadata = client.get(
        f"/api/v1/transactions/{transaction['id']}/receipt", headers=headers
    )
    assert metadata.status_code == 200
    assert metadata.json()["data"]["id"] == receipt["id"]

    link = client.get(
        f"/api/v1/transactions/{transaction['id']}/receipt/url", headers=headers
    )
    assert link.status_code == 200
    url = link.json()["data"]["url"]

    download = client.get(urlparse(url).path)
    assert download.status_code == 200
    assert download.content == PNG_BYTES
    assert download.headers["content-type"] == "image/png"


def test_pdf_receipts_are_allowed(client, make_token):
    headers = setup_user(client, make_token)
    transaction = make_transaction(client, headers)

    response = upload(
        client, headers, transaction["id"], PDF_BYTES, "invoice.pdf", "application/pdf"
    )

    assert response.status_code == 201
    assert response.json()["data"]["mime_type"] == "application/pdf"


def test_one_receipt_per_transaction(client, make_token):
    headers = setup_user(client, make_token)
    transaction = make_transaction(client, headers)

    assert upload(client, headers, transaction["id"]).status_code == 201
    second = upload(client, headers, transaction["id"])

    assert second.status_code == 409
    assert second.json()["error"]["code"] == "receipt_exists"


def test_unsupported_file_type_is_rejected_by_magic_bytes(client, make_token):
    headers = setup_user(client, make_token)
    transaction = make_transaction(client, headers)

    response = upload(
        client,
        headers,
        transaction["id"],
        b"GIF89a not really allowed",
        "receipt.gif",
        "image/png",
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "unsupported_file_type"


def test_files_over_five_megabytes_are_rejected(client, make_token):
    headers = setup_user(client, make_token)
    transaction = make_transaction(client, headers)

    oversized = b"\x89PNG\r\n\x1a\n" + b"\x00" * receipt_storage.MAX_RECEIPT_BYTES
    response = upload(client, headers, transaction["id"], oversized)

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"


def test_receipts_are_private_to_the_owner(client, make_token):
    headers_a = setup_user(client, make_token, "a@example.com")
    headers_b = setup_user(client, make_token, "b@example.com")
    transaction = make_transaction(client, headers_a)
    upload(client, headers_a, transaction["id"])

    assert (
        client.get(
            f"/api/v1/transactions/{transaction['id']}/receipt", headers=headers_b
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/transactions/{transaction['id']}/receipt/url", headers=headers_b
        ).status_code
        == 404
    )
    assert upload(client, headers_b, transaction["id"]).status_code == 404
    assert (
        client.delete(
            f"/api/v1/transactions/{transaction['id']}/receipt", headers=headers_b
        ).status_code
        == 404
    )


def test_receipt_can_be_deleted(client, make_token):
    headers = setup_user(client, make_token)
    transaction = make_transaction(client, headers)
    upload(client, headers, transaction["id"])

    deleted = client.delete(
        f"/api/v1/transactions/{transaction['id']}/receipt", headers=headers
    )
    assert deleted.status_code == 200

    assert (
        client.get(
            f"/api/v1/transactions/{transaction['id']}/receipt", headers=headers
        ).status_code
        == 404
    )
    assert upload(client, headers, transaction["id"]).status_code == 201


def test_expired_local_links_are_rejected(client):
    token = receipt_storage.make_local_token("some/path.png", -1)

    response = client.get(f"/api/v1/receipts/local/{token}")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "receipt_link_expired"


def test_tampered_local_links_are_rejected(client):
    token = receipt_storage.make_local_token("some/path.png", 300)
    payload, signature = token.split(".")
    tampered = f"{payload}.{signature[:-2]}xx"

    response = client.get(f"/api/v1/receipts/local/{tampered}")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "invalid_receipt_link"
