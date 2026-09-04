from __future__ import annotations

import json
from functools import lru_cache

import httpx
from fastapi import APIRouter, Header, HTTPException, Request

from backend.app.adapters.razorpay import RazorpayAdapter
from backend.app.core.config import get_settings
from backend.app.services.razorpay_integration import RazorpayIntegrationService
from backend.app.storage.factory import create_recovery_repository

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@lru_cache
def get_integration_service(
    database_path: str,
    database_url: str = "",
) -> RazorpayIntegrationService:
    return RazorpayIntegrationService(
        repository=create_recovery_repository(
            database_url=database_url,
            database_path=database_path,
        )
    )


def _adapter() -> RazorpayAdapter:
    settings = get_settings()
    return RazorpayAdapter(
        key_id=settings.razorpay_key_id,
        key_secret=settings.razorpay_key_secret,
        webhook_secret=settings.razorpay_webhook_secret,
    )


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None),
    x_razorpay_event_id: str | None = Header(default=None),
):
    raw_body = await request.body()
    settings = get_settings()

    if not x_razorpay_signature:
        raise HTTPException(status_code=401, detail="Missing Razorpay signature")
    if not x_razorpay_event_id:
        raise HTTPException(status_code=400, detail="Missing Razorpay event id")
    if not settings.webhook_configured:
        raise HTTPException(status_code=503, detail="Webhook secret not configured")
    if not settings.durable_database_configured:
        raise HTTPException(status_code=503, detail="Durable database not configured")

    adapter = _adapter()
    if not adapter.verify_webhook_signature(raw_body, x_razorpay_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    try:
        integration_service = get_integration_service(
            settings.recoveriq_database_path,
            settings.database_url,
        )
        integration_service.safety.autonomous_limit_paise = (
            settings.recoveriq_autonomous_limit_paise
        )
        return await integration_service.process(
            x_razorpay_event_id,
            payload,
            mode=settings.recoveriq_mode,
            execute_razorpay_actions=(
                settings.recoveriq_execute_razorpay_actions
                and settings.razorpay_api_configured
            ),
            adapter=adapter,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail="Razorpay execution API returned an error",
        ) from exc
