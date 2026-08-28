import asyncio

from backend.app.adapters.razorpay import RazorpayAdapter
from backend.app.domain.events import (
    map_failure_reason,
    normalize_payment_event,
)
from backend.app.services.razorpay_integration import RazorpayIntegrationService


def payment_payload(
    event: str,
    *,
    reason: str = "insufficient_funds",
    amount_paise: int = 499900,
) -> dict:
    return {
        "entity": "event",
        "event": event,
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test123",
                    "amount": amount_paise,
                    "currency": "INR",
                    "status": "failed" if event == "payment.failed" else "captured",
                    "order_id": "order_test123",
                    "method": "upi",
                    "email": "customer@example.com",
                    "contact": "+919999999999",
                    "error_reason": reason if event == "payment.failed" else None,
                    "error_source": "bank" if event == "payment.failed" else None,
                    "created_at": 1780000000,
                }
            }
        },
    }


def inert_adapter() -> RazorpayAdapter:
    return RazorpayAdapter("", "", "webhook-secret")


def test_failed_payment_is_normalized_and_mapped():
    event = normalize_payment_event(
        "evt_failed_1",
        payment_payload("payment.failed"),
    )

    assert event.payment_id == "pay_test123"
    assert event.amount_paise == 499900
    assert event.payment_method == "upi"
    assert map_failure_reason(event) == "INSUFFICIENT_FUNDS"


def test_captured_event_closes_case():
    service = RazorpayIntegrationService()

    result = asyncio.run(
        service.process(
            "evt_captured_1",
            payment_payload("payment.captured"),
            mode="shadow",
            execute_razorpay_actions=False,
            adapter=inert_adapter(),
        )
    )

    assert result["status"] == "case_closed"
    assert service.repository.get_case("pay_test123")["status"] == "RECOVERED"
    assert service.repository.counts()["outcomes"] == 1


def test_captured_before_failed_does_not_reopen_case():
    service = RazorpayIntegrationService()

    asyncio.run(
        service.process(
            "evt_captured_first",
            payment_payload("payment.captured"),
            mode="shadow",
            execute_razorpay_actions=False,
            adapter=inert_adapter(),
        )
    )
    result = asyncio.run(
        service.process(
            "evt_failed_late",
            payment_payload("payment.failed"),
            mode="shadow",
            execute_razorpay_actions=False,
            adapter=inert_adapter(),
        )
    )

    assert result["status"] == "stale_failure_ignored"
    assert service.repository.get_case("pay_test123")["status"] == "RECOVERED"


def test_duplicate_event_is_idempotently_ignored():
    service = RazorpayIntegrationService()
    kwargs = dict(
        mode="shadow",
        execute_razorpay_actions=False,
        adapter=inert_adapter(),
    )

    first = asyncio.run(
        service.process(
            "evt_same",
            payment_payload("payment.failed"),
            **kwargs,
        )
    )
    second = asyncio.run(
        service.process(
            "evt_same",
            payment_payload("payment.failed"),
            **kwargs,
        )
    )

    assert first["status"] == "decision_recorded"
    assert first["execution_status"] == "shadow_logged"
    assert second == {"status": "duplicate_ignored", "event_id": "evt_same"}


def test_high_value_autonomous_action_is_escalated():
    service = RazorpayIntegrationService()

    result = asyncio.run(
        service.process(
            "evt_high_value",
            payment_payload("payment.failed", amount_paise=2_500_000),
            mode="autonomous",
            execute_razorpay_actions=True,
            adapter=inert_adapter(),
        )
    )

    assert result["policy_decision"] == "REQUIRE_APPROVAL"
    assert result["execution_status"] == "awaiting_human_approval"
