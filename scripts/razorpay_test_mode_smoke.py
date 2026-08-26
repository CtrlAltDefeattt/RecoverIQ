from __future__ import annotations

import argparse
import asyncio
import time

from backend.app.adapters.razorpay import RazorpayAdapter
from backend.app.core.config import get_settings


async def run(amount_paise: int) -> None:
    settings = get_settings()
    if not settings.razorpay_api_configured:
        raise SystemExit(
            "Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET before running the smoke test."
        )
    if not settings.razorpay_key_id.startswith("rzp_test_"):
        raise SystemExit("Smoke test requires Razorpay Test Mode credentials.")

    adapter = RazorpayAdapter(
        key_id=settings.razorpay_key_id,
        key_secret=settings.razorpay_key_secret,
        webhook_secret=settings.razorpay_webhook_secret,
    )
    reference = f"recoveriq-smoke-{int(time.time())}"
    link = await adapter.create_payment_link(
        amount_paise=amount_paise,
        reference_id=reference,
        description="RecoverIQ Test Mode integration smoke test",
        reminder_enable=False,
    )
    print(
        {
            "id": link.get("id"),
            "status": link.get("status"),
            "short_url": link.get("short_url"),
            "reference_id": link.get("reference_id"),
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--amount-paise", type=int, default=100)
    args = parser.parse_args()
    asyncio.run(run(args.amount_paise))


if __name__ == "__main__":
    main()
