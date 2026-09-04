from __future__ import annotations

import hashlib
import hmac
from typing import Literal

import httpx


class RazorpayAdapter:
    BASE_URL = "https://api.razorpay.com/v1"

    def __init__(
        self,
        key_id: str,
        key_secret: str,
        webhook_secret: str,
        *,
        base_url: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.key_id = key_id
        self.key_secret = key_secret
        self.webhook_secret = webhook_secret
        self.base_url = (base_url or self.BASE_URL).rstrip("/")
        self.transport = transport

    def verify_webhook_signature(
        self,
        raw_body: bytes,
        received_signature: str,
    ) -> bool:
        if not self.webhook_secret:
            return False
        expected = hmac.new(
            self.webhook_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, received_signature)

    async def create_payment_link(
        self,
        amount_paise: int,
        reference_id: str,
        description: str,
        customer_name: str | None = None,
        customer_email: str | None = None,
        customer_contact: str | None = None,
        accept_partial: bool = False,
        first_min_partial_amount: int | None = None,
        reminder_enable: bool = False,
        notify_sms: bool = False,
        notify_email: bool = False,
    ) -> dict:
        self._validate_api_configuration()
        if amount_paise <= 0:
            raise ValueError("amount_paise must be positive")
        if not reference_id or len(reference_id) > 40:
            raise ValueError("reference_id must contain 1 to 40 characters")
        if not description or len(description) > 2048:
            raise ValueError("description must contain 1 to 2048 characters")
        if first_min_partial_amount is not None:
            if not accept_partial:
                raise ValueError(
                    "first_min_partial_amount requires accept_partial=True"
                )
            if not 100 <= first_min_partial_amount <= amount_paise:
                raise ValueError(
                    "first_min_partial_amount must be between 100 and amount"
                )

        payload = {
            "amount": amount_paise,
            "currency": "INR",
            "reference_id": reference_id,
            "description": description,
            "accept_partial": accept_partial,
            "reminder_enable": reminder_enable,
        }
        if first_min_partial_amount is not None:
            payload["first_min_partial_amount"] = first_min_partial_amount

        if notify_sms or notify_email:
            payload["notify"] = {
                "sms": notify_sms,
                "email": notify_email,
            }

        customer = {}
        if customer_name:
            customer["name"] = customer_name
        if customer_email:
            customer["email"] = customer_email
        if customer_contact:
            customer["contact"] = customer_contact
        if customer and not customer_name:
            raise ValueError(
                "customer_name is required when email or contact is provided"
            )
        if customer:
            payload["customer"] = customer

        async with self._client() as client:
            response = await client.post(
                "/payment_links",
                auth=(self.key_id, self.key_secret),
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def send_payment_link_notification(
        self,
        payment_link_id: str,
        medium: Literal["sms", "email"],
    ) -> dict:
        self._validate_api_configuration()
        if not payment_link_id.startswith("plink_"):
            raise ValueError("payment_link_id must start with 'plink_'")
        if medium not in {"sms", "email"}:
            raise ValueError("medium must be 'sms' or 'email'")

        async with self._client() as client:
            response = await client.post(
                f"/payment_links/{payment_link_id}/notify_by/{medium}",
                auth=(self.key_id, self.key_secret),
            )
            response.raise_for_status()
            return response.json()

    def _validate_api_configuration(self) -> None:
        if not self.key_id or not self.key_secret:
            raise RuntimeError("Razorpay API credentials are not configured")

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            timeout=20,
            transport=self.transport,
        )
