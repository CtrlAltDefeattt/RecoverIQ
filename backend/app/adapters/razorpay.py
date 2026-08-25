from __future__ import annotations
import hmac
import hashlib
import httpx


class RazorpayAdapter:
    BASE_URL = "https://api.razorpay.com/v1"

    def __init__(self, key_id: str, key_secret: str, webhook_secret: str):
        self.key_id = key_id
        self.key_secret = key_secret
        self.webhook_secret = webhook_secret

    def verify_webhook_signature(
        self,
        raw_body: bytes,
        received_signature: str,
    ) -> bool:
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
    ) -> dict:
        payload = {
            "amount": amount_paise,
            "currency": "INR",
            "reference_id": reference_id,
            "description": description,
            "accept_partial": accept_partial,
        }

        customer = {}
        if customer_name:
            customer["name"] = customer_name
        if customer_email:
            customer["email"] = customer_email
        if customer_contact:
            customer["contact"] = customer_contact
        if customer:
            payload["customer"] = customer

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{self.BASE_URL}/payment_links",
                auth=(self.key_id, self.key_secret),
                json=payload,
            )
            response.raise_for_status()
            return response.json()
