import sqlite3

import pytest

from backend.app.domain.events import map_failure_reason, normalize_payment_event
from backend.app.storage.sqlite import SQLiteRecoveryRepository
from tests.test_razorpay_events import payment_payload


def normalized(event_id: str, event_type: str = "payment.failed"):
    return normalize_payment_event(event_id, payment_payload(event_type))


def test_event_id_is_enforced_by_sqlite_unique_constraint(tmp_path):
    repository = SQLiteRecoveryRepository(str(tmp_path / "recoveriq.sqlite3"))
    payload = payment_payload("payment.failed")

    assert repository.claim_event("evt_unique", payload) is True
    assert repository.claim_event("evt_unique", payload) is False
    assert repository.counts()["webhook_events"] == 1


def test_case_and_capture_survive_repository_restart(tmp_path):
    database = tmp_path / "recoveriq.sqlite3"
    first = SQLiteRecoveryRepository(str(database))
    failed = normalized("evt_failed")
    first.claim_event(failed.event_id, payment_payload("payment.failed"))
    first.attach_event_identity(failed.event_id, failed.event_type, failed.payment_id)
    first.upsert_failed_case(failed, map_failure_reason(failed))
    first.close()

    second = SQLiteRecoveryRepository(str(database))
    case = second.get_case("pay_test123")

    assert case["status"] == "AT_RISK"
    assert second.claim_event("evt_failed", payment_payload("payment.failed")) is False


def test_capture_is_terminal_and_late_failure_does_not_reopen():
    repository = SQLiteRecoveryRepository(":memory:")
    captured = normalized("evt_captured", "payment.captured")
    repository.claim_event(captured.event_id, payment_payload("payment.captured"))
    repository.attach_event_identity(
        captured.event_id,
        captured.event_type,
        captured.payment_id,
    )
    repository.close_recovered_case(captured)

    late = normalized("evt_late")
    repository.claim_event(late.event_id, payment_payload("payment.failed"))
    case, stale = repository.upsert_failed_case(late, map_failure_reason(late))

    assert stale is True
    assert case["status"] == "RECOVERED"
    assert repository.get_case("pay_test123")["status"] == "RECOVERED"


def test_ledgers_preserve_decision_action_and_audit():
    repository = SQLiteRecoveryRepository(":memory:")
    event = normalized("evt_ledger")
    repository.claim_event(event.event_id, payment_payload("payment.failed"))
    repository.attach_event_identity(event.event_id, event.event_type, event.payment_id)
    repository.upsert_failed_case(event, map_failure_reason(event))
    decision_id = repository.record_decision(
        event_id=event.event_id,
        payment_id=event.payment_id,
        mode="shadow",
        recommended_action="PAYMENT_LINK",
        policy_decision="ALLOW",
        policy_reason="POLICY_OK",
        execution_status="shadow_logged",
    )
    repository.record_action(
        decision_id=decision_id,
        payment_id=event.payment_id,
        idempotency_key="pay_test123:PAYMENT_LINK:1",
        action="PAYMENT_LINK",
        status="shadow_logged",
    )

    counts = repository.counts()
    audit_types = [
        item["event_type"]
        for item in repository.list_audit("case", event.payment_id)
    ]

    assert counts["decisions"] == 1
    assert counts["actions"] == 1
    assert "DECISION_RECORDED" in audit_types
    assert "ACTION_RECORDED" in audit_types


def test_action_idempotency_key_is_database_enforced():
    repository = SQLiteRecoveryRepository(":memory:")
    event = normalized("evt_action")
    repository.claim_event(event.event_id, payment_payload("payment.failed"))
    repository.attach_event_identity(event.event_id, event.event_type, event.payment_id)
    repository.upsert_failed_case(event, map_failure_reason(event))
    decision_id = repository.record_decision(
        event_id=event.event_id,
        payment_id=event.payment_id,
        mode="autonomous",
        recommended_action="PAYMENT_LINK",
        policy_decision="ALLOW",
        policy_reason="POLICY_OK",
        execution_status="pending",
    )
    repository.record_action(
        decision_id=decision_id,
        payment_id=event.payment_id,
        idempotency_key="stable-key",
        action="PAYMENT_LINK",
        status="pending",
    )
    second_event = normalized("evt_action_2")
    repository.claim_event(
        second_event.event_id,
        payment_payload("payment.failed"),
    )
    repository.attach_event_identity(
        second_event.event_id,
        second_event.event_type,
        second_event.payment_id,
    )
    repository.upsert_failed_case(second_event, map_failure_reason(second_event))
    second_decision_id = repository.record_decision(
        event_id=second_event.event_id,
        payment_id=second_event.payment_id,
        mode="autonomous",
        recommended_action="PAYMENT_LINK",
        policy_decision="ALLOW",
        policy_reason="POLICY_OK",
        execution_status="pending",
    )

    with pytest.raises(sqlite3.IntegrityError):
        repository.record_action(
            decision_id=second_decision_id,
            payment_id=event.payment_id,
            idempotency_key="stable-key",
            action="PAYMENT_LINK",
            status="pending",
        )
