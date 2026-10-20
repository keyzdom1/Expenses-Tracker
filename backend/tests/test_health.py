"""Phase 1 smoke test: the API boots and uses the standard envelopes."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_success_envelope():
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "ok"
    assert body["data"]["api_prefix"] == "/api/v1"
    assert "meta" in body


def test_request_id_header_is_present():
    response = client.get("/health")

    assert response.headers.get("X-Request-ID")


def test_request_id_is_echoed_back_when_supplied():
    response = client.get("/health", headers={"X-Request-ID": "test-rid-123"})

    assert response.headers["X-Request-ID"] == "test-rid-123"


def test_openapi_document_is_available():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Expense Tracker API"
