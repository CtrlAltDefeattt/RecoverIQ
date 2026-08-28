import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from backend.app.api.webhooks import get_integration_service
from backend.app.core.config import get_settings
from backend.app.main import app
from tests.test_razorpay_events import payment_payload


def configure_test_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "webhook-secret")
    monkeypatch.setenv("RECOVERIQ_MODE", "shadow")
    monkeypatch.setenv("RECOVERIQ_EXECUTE_RAZORPAY_ACTIONS", "false")
    monkeypatch.setenv(
        "RECOVERIQ_DATABASE_PATH",
        str(tmp_path / "webhook.sqlite3"),
    )
    get_settings.cache_clear()
    get_integration_service.cache_clear()


def signed_headers(raw_body: bytes, event_id: str) -> dict:
    signature = hmac.new(
        b"webhook-secret",
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return {
        "x-razorpay-signature": signature,
        "x-razorpay-event-id": event_id,
        "content-type": "application/json",
    }


def test_signed_failed_webhook_reaches_shadow_decision(monkeypatch, tmp_path):
    configure_test_environment(monkeypatch, tmp_path)
    raw_body = json.dumps(
        payment_payload("payment.failed"),
        separators=(",", ":"),
    ).encode()

    with TestClient(app) as client:
        response = client.post(
            "/webhooks/razorpay",
            content=raw_body,
            headers=signed_headers(raw_body, "evt_api_failed"),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "decision_recorded"
    assert body["execution_status"] == "shadow_logged"
    assert body["recommended_action"]
    service = get_integration_service(str(tmp_path / "webhook.sqlite3"))
    assert service.repository.counts()["decisions"] == 1
    assert service.repository.counts()["actions"] == 1


def test_duplicate_signed_webhook_is_ignored(monkeypatch, tmp_path):
    configure_test_environment(monkeypatch, tmp_path)
    raw_body = json.dumps(payment_payload("payment.failed")).encode()
    headers = signed_headers(raw_body, "evt_api_duplicate")

    with TestClient(app) as client:
        first = client.post("/webhooks/razorpay", content=raw_body, headers=headers)
        second = client.post("/webhooks/razorpay", content=raw_body, headers=headers)

    assert first.status_code == 200
    assert second.json()["status"] == "duplicate_ignored"


def test_invalid_signature_is_rejected(monkeypatch, tmp_path):
    configure_test_environment(monkeypatch, tmp_path)
    raw_body = json.dumps(payment_payload("payment.failed")).encode()
    headers = signed_headers(raw_body, "evt_api_bad_signature")
    headers["x-razorpay-signature"] = "invalid"

    with TestClient(app) as client:
        response = client.post(
            "/webhooks/razorpay",
            content=raw_body,
            headers=headers,
        )

    assert response.status_code == 401


def test_readiness_does_not_expose_secrets(monkeypatch, tmp_path):
    configure_test_environment(monkeypatch, tmp_path)

    with TestClient(app) as client:
        response = client.get("/readiness")

    assert response.status_code == 200
    assert response.json()["webhook_configured"] is True
    assert "webhook-secret" not in response.text
