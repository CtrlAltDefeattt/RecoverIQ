from __future__ import annotations

from dataclasses import dataclass


SUPPORTED_PAYMENT_EVENTS = {"payment.failed", "payment.captured"}


class UnsupportedWebhookEvent(ValueError):
    pass


@dataclass(frozen=True)
class NormalizedPaymentEvent:
    event_id: str
    event_type: str
    payment_id: str
    amount_paise: int
    currency: str
    payment_method: str
    order_id: str | None
    error_reason: str | None
    error_source: str | None
    customer_email: str | None
    customer_contact: str | None
    created_at: int | None


def normalize_payment_event(
    event_id: str,
    payload: dict,
) -> NormalizedPaymentEvent:
    event_type = payload.get("event")
    if event_type not in SUPPORTED_PAYMENT_EVENTS:
        raise UnsupportedWebhookEvent(str(event_type))

    payment = (
        payload.get("payload", {})
        .get("payment", {})
        .get("entity")
    )
    if not isinstance(payment, dict):
        raise ValueError("Missing payload.payment.entity")

    payment_id = payment.get("id")
    amount_paise = payment.get("amount")
    if not payment_id or not isinstance(amount_paise, int) or amount_paise <= 0:
        raise ValueError("Payment id and positive integer amount are required")

    return NormalizedPaymentEvent(
        event_id=event_id,
        event_type=event_type,
        payment_id=payment_id,
        amount_paise=amount_paise,
        currency=payment.get("currency") or "INR",
        payment_method=payment.get("method") or "unknown",
        order_id=payment.get("order_id"),
        error_reason=payment.get("error_reason"),
        error_source=payment.get("error_source"),
        customer_email=payment.get("email"),
        customer_contact=payment.get("contact"),
        created_at=payment.get("created_at"),
    )


def map_failure_reason(event: NormalizedPaymentEvent) -> str:
    reason = (event.error_reason or "").lower()
    source = (event.error_source or "").lower()

    if reason in {"insufficient_funds", "low_balance"}:
        return "INSUFFICIENT_FUNDS"
    if reason in {
        "authentication_failed",
        "incorrect_otp",
        "incorrect_pin",
        "otp_attempts_exceeded",
    }:
        return "AUTHENTICATION_FAILED"
    if reason in {"gateway_error", "server_error", "timed_out"} or source in {
        "internal",
        "gateway",
    }:
        return "NETWORK_ERROR"
    return "BANK_DECLINED"
