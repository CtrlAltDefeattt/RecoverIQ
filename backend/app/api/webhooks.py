from __future__ import annotations
import json
import os

from fastapi import APIRouter, Header, HTTPException, Request
from backend.app.adapters.razorpay import RazorpayAdapter

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
PROCESSED_EVENT_IDS: set[str] = set()


def _adapter() -> RazorpayAdapter:
    return RazorpayAdapter(
        key_id=os.getenv("RAZORPAY_KEY_ID", ""),
        key_secret=os.getenv("RAZORPAY_KEY_SECRET", ""),
        webhook_secret=os.getenv("RAZORPAY_WEBHOOK_SECRET", ""),
    )


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None),
    x_razorpay_event_id: str | None = Header(default=None),
):
    raw_body = await request.body()

    if not x_razorpay_signature:
        raise HTTPException(status_code=401, detail="Missing Razorpay signature")

    adapter = _adapter()
    if not adapter.webhook_secret:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    if not adapter.verify_webhook_signature(raw_body, x_razorpay_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    if x_razorpay_event_id and x_razorpay_event_id in PROCESSED_EVENT_IDS:
        return {"status": "duplicate_ignored"}

    payload = json.loads(raw_body.decode("utf-8"))
    event = payload.get("event")

    if x_razorpay_event_id:
        PROCESSED_EVENT_IDS.add(x_razorpay_event_id)

    return {
        "status": "accepted",
        "event": event,
        "event_id": x_razorpay_event_id,
    }
