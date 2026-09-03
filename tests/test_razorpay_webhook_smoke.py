import hashlib
import hmac
import json

import httpx

from scripts.razorpay_webhook_smoke import (
    build_payload,
    post_webhook,
    signed_request,
)


def test_signed_request_uses_exact_body():
    payload = build_payload(
        event="payment.failed",
        payment_id="pay_demo",
        amount_paise=499_900,
        created_at=1_780_000_000,
    )

    raw_body, headers = signed_request(payload, "evt_demo", "secret")

    assert json.loads(raw_body) == payload
    assert headers["x-razorpay-event-id"] == "evt_demo"
    assert headers["x-razorpay-signature"] == hmac.new(
        b"secret",
        raw_body,
        hashlib.sha256,
    ).hexdigest()


def test_post_webhook_targets_recoveriq_route():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/webhooks/razorpay"
        assert request.headers["x-razorpay-event-id"] == "evt_demo"
        return httpx.Response(200, json={"status": "decision_recorded"})

    result = post_webhook(
        api_url="https://example.test/",
        raw_body=b"{}",
        headers={"x-razorpay-event-id": "evt_demo"},
        timeout=1,
        transport=httpx.MockTransport(handler),
    )

    assert result == {"status": "decision_recorded"}
