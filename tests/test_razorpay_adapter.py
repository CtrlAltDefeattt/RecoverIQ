import asyncio
import json

import httpx

from backend.app.adapters.razorpay import RazorpayAdapter


def test_create_payment_link_sends_bounded_payload():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["payload"] = json.loads(request.content)
        captured["authorization"] = request.headers.get("authorization")
        return httpx.Response(
            200,
            json={
                "id": "plink_test123456",
                "status": "created",
                "short_url": "https://rzp.io/i/test",
            },
        )

    adapter = RazorpayAdapter(
        "rzp_test_key",
        "test_secret",
        "webhook_secret",
        transport=httpx.MockTransport(handler),
    )
    result = asyncio.run(
        adapter.create_payment_link(
            amount_paise=499900,
            reference_id="recover_pay_test123",
            description="Recover failed payment",
            accept_partial=True,
            first_min_partial_amount=10000,
        )
    )

    assert result["status"] == "created"
    assert captured["path"] == "/v1/payment_links"
    assert captured["payload"]["amount"] == 499900
    assert captured["payload"]["accept_partial"] is True
    assert captured["payload"]["first_min_partial_amount"] == 10000
    assert captured["authorization"].startswith("Basic ")


def test_notification_endpoint_uses_requested_medium():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        return httpx.Response(200, json={"success": True})

    adapter = RazorpayAdapter(
        "rzp_test_key",
        "test_secret",
        "webhook_secret",
        transport=httpx.MockTransport(handler),
    )
    result = asyncio.run(
        adapter.send_payment_link_notification(
            "plink_test123456",
            "email",
        )
    )

    assert result == {"success": True}
    assert captured["path"] == (
        "/v1/payment_links/plink_test123456/notify_by/email"
    )


def test_api_methods_fail_closed_without_credentials():
    adapter = RazorpayAdapter("", "", "webhook_secret")

    try:
        asyncio.run(
            adapter.create_payment_link(
                amount_paise=100,
                reference_id="test",
                description="test",
            )
        )
    except RuntimeError as exc:
        assert "not configured" in str(exc)
    else:
        raise AssertionError("Expected missing credentials to fail closed")
