import asyncio
import os
from uuid import uuid4

import pytest

from backend.app.services.razorpay_integration import RazorpayIntegrationService
from backend.app.storage.postgres import PostgresRecoveryRepository
from tests.test_razorpay_events import inert_adapter, payment_payload


@pytest.mark.skipif(
    not os.getenv("RECOVERIQ_TEST_DATABASE_URL"),
    reason="RECOVERIQ_TEST_DATABASE_URL is not configured",
)
def test_neon_repository_preserves_idempotent_recovery_ledger():
    suffix = uuid4().hex
    event_id = f"evt_neon_{suffix}"
    payment_id = f"pay_neon_{suffix}"
    payload = payment_payload("payment.failed")
    payload["payload"]["payment"]["entity"]["id"] = payment_id

    repository = PostgresRecoveryRepository(
        os.environ["RECOVERIQ_TEST_DATABASE_URL"]
    )
    service = RazorpayIntegrationService(repository=repository)
    kwargs = {
        "mode": "shadow",
        "execute_razorpay_actions": False,
        "adapter": inert_adapter(),
    }

    first = asyncio.run(service.process(event_id, payload, **kwargs))
    duplicate = asyncio.run(service.process(event_id, payload, **kwargs))

    assert first["status"] == "decision_recorded"
    assert duplicate == {"status": "duplicate_ignored", "event_id": event_id}
    assert repository.get_case(payment_id)["status"] == "AT_RISK"
    assert len(repository.list_case_decisions(payment_id)) == 1
    assert len(repository.list_case_actions(payment_id)) == 1
    assert repository.ping() is True
