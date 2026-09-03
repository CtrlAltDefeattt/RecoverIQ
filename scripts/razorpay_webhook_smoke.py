from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import time
import uuid

import httpx


DEFAULT_API_URL = "https://recoveriq-api.vercel.app"


def build_payload(
    *,
    event: str,
    payment_id: str,
    amount_paise: int,
    created_at: int,
) -> dict:
    if event not in {"payment.failed", "payment.captured"}:
        raise ValueError("event must be payment.failed or payment.captured")
    return {
        "entity": "event",
        "event": event,
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "amount": amount_paise,
                    "currency": "INR",
                    "status": "failed" if event == "payment.failed" else "captured",
                    "order_id": f"order_{payment_id}",
                    "method": "upi",
                    "email": "recoveriq-demo@example.invalid",
                    "error_reason": (
                        "insufficient_funds" if event == "payment.failed" else None
                    ),
                    "error_source": "bank" if event == "payment.failed" else None,
                    "created_at": created_at,
                }
            }
        },
    }


def signed_request(payload: dict, event_id: str, secret: str) -> tuple[bytes, dict]:
    raw_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    signature = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return raw_body, {
        "content-type": "application/json",
        "x-razorpay-event-id": event_id,
        "x-razorpay-signature": signature,
    }


def post_webhook(
    *,
    api_url: str,
    raw_body: bytes,
    headers: dict,
    timeout: float,
    transport: httpx.BaseTransport | None = None,
) -> dict:
    with httpx.Client(timeout=timeout, transport=transport) as client:
        response = client.post(
            f"{api_url.rstrip('/')}/webhooks/razorpay",
            content=raw_body,
            headers=headers,
        )
        response.raise_for_status()
        return response.json()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Send a signed synthetic Razorpay event to a RecoverIQ API."
    )
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument(
        "--event",
        choices=("payment.failed", "payment.captured"),
        default="payment.failed",
    )
    parser.add_argument("--amount-paise", type=int, default=499_900)
    parser.add_argument("--payment-id")
    parser.add_argument("--event-id")
    parser.add_argument("--verify-idempotency", action="store_true")
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()

    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
    if not secret:
        raise SystemExit("Set RAZORPAY_WEBHOOK_SECRET in the shell before running.")
    if args.amount_paise <= 0:
        raise SystemExit("--amount-paise must be positive.")

    suffix = uuid.uuid4().hex[:12]
    payment_id = args.payment_id or f"pay_recoveriq_{suffix}"
    event_id = args.event_id or f"evt_recoveriq_{suffix}"
    payload = build_payload(
        event=args.event,
        payment_id=payment_id,
        amount_paise=args.amount_paise,
        created_at=int(time.time()),
    )
    raw_body, headers = signed_request(payload, event_id, secret)
    first = post_webhook(
        api_url=args.api_url,
        raw_body=raw_body,
        headers=headers,
        timeout=args.timeout,
    )
    print(json.dumps({"delivery": 1, "response": first}, indent=2))

    if args.verify_idempotency:
        second = post_webhook(
            api_url=args.api_url,
            raw_body=raw_body,
            headers=headers,
            timeout=args.timeout,
        )
        print(json.dumps({"delivery": 2, "response": second}, indent=2))
        if second.get("status") != "duplicate_ignored":
            raise SystemExit("Duplicate delivery was not ignored.")


if __name__ == "__main__":
    main()
