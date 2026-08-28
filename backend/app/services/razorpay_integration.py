from __future__ import annotations

from typing import Literal

import httpx

from backend.app.adapters.razorpay import RazorpayAdapter
from backend.app.domain.events import (
    UnsupportedWebhookEvent,
    map_failure_reason,
    normalize_payment_event,
)
from backend.app.domain.models import RecoveryAction, RecoveryContext
from backend.app.policies.baselines import RuleBasedPolicy
from backend.app.safety.engine import CONTACT_ACTIONS, SafetyEngine
from backend.app.storage.sqlite import SQLiteRecoveryRepository


Mode = Literal["shadow", "assisted", "autonomous"]
LINK_ACTIONS = {
    RecoveryAction.PAYMENT_LINK,
    RecoveryAction.ALT_PAYMENT,
    RecoveryAction.PARTIAL_PAYMENT,
}


class RazorpayIntegrationService:
    """Durable webhook-to-decision integration with an auditable action ledger."""

    def __init__(
        self,
        policy: RuleBasedPolicy | None = None,
        safety: SafetyEngine | None = None,
        repository: SQLiteRecoveryRepository | None = None,
    ):
        self.policy = policy or RuleBasedPolicy()
        self.safety = safety or SafetyEngine()
        self.repository = repository or SQLiteRecoveryRepository(":memory:")

    def reset(self) -> None:
        self.repository.clear_all()

    async def process(
        self,
        event_id: str,
        payload: dict,
        *,
        mode: Mode,
        execute_razorpay_actions: bool,
        adapter: RazorpayAdapter,
    ) -> dict:
        if not self.repository.claim_event(event_id, payload):
            return {"status": "duplicate_ignored", "event_id": event_id}

        try:
            event = normalize_payment_event(event_id, payload)
        except UnsupportedWebhookEvent as exc:
            result = {
                "status": "unsupported_event_ignored",
                "event_id": event_id,
                "event": str(exc),
            }
            self.repository.complete_event(event_id, "IGNORED", result)
            return result
        except ValueError as exc:
            result = {
                "status": "invalid_event",
                "event_id": event_id,
                "reason": str(exc),
            }
            self.repository.complete_event(event_id, "REJECTED", result)
            raise

        self.repository.attach_event_identity(
            event.event_id,
            event.event_type,
            event.payment_id,
        )

        if event.event_type == "payment.captured":
            self.repository.close_recovered_case(event)
            result = {
                "status": "case_closed",
                "event_id": event_id,
                "event": event.event_type,
                "payment_id": event.payment_id,
                "recovered_amount_paise": event.amount_paise,
            }
            self.repository.complete_event(event_id, "PROCESSED", result)
            return result

        case, stale = self.repository.upsert_failed_case(
            event,
            map_failure_reason(event),
        )
        if stale:
            result = {
                "status": "stale_failure_ignored",
                "event_id": event_id,
                "event": event.event_type,
                "payment_id": event.payment_id,
                "reason": "PAYMENT_ALREADY_CAPTURED",
            }
            self.repository.complete_event(event_id, "IGNORED", result)
            return result

        context = self._context_from_failed_payment(event, case)
        reviewable_actions = self.safety.reviewable_actions(context)
        action = self.policy.select_action(
            context,
            allowed_actions=reviewable_actions,
        )
        safety = self.safety.evaluate(context, action)
        blocked_action_reasons = {}
        for candidate in RecoveryAction:
            evaluation = self.safety.evaluate(context, candidate)
            if evaluation.decision.value == "BLOCK":
                blocked_action_reasons[candidate.value] = evaluation.reason

        execution_status = self._execution_status(
            mode,
            safety.decision.value,
            action,
            execute_razorpay_actions,
        )
        result = {
            "status": "decision_recorded",
            "event_id": event_id,
            "event": event.event_type,
            "payment_id": event.payment_id,
            "amount_paise": event.amount_paise,
            "mode": mode,
            "recommended_action": action.value,
            "policy_decision": safety.decision.value,
            "policy_reason": safety.reason,
            "blocked_action_reasons": blocked_action_reasons,
            "execution_status": execution_status,
        }
        decision_id = self.repository.record_decision(
            event_id=event_id,
            payment_id=event.payment_id,
            mode=mode,
            recommended_action=action.value,
            policy_decision=safety.decision.value,
            policy_reason=safety.reason,
            execution_status=execution_status,
        )
        action_id = self.repository.record_action(
            decision_id=decision_id,
            payment_id=event.payment_id,
            idempotency_key=f"{event.payment_id}:{action.value}:{case['version']}",
            action=action.value,
            status=execution_status,
        )

        if execution_status != "pending_execution":
            self.repository.complete_event(event_id, "PROCESSED", result)
            return result

        try:
            link = await adapter.create_payment_link(
                amount_paise=event.amount_paise,
                reference_id=f"recover_{event.payment_id}"[:40],
                description=f"Recover failed payment {event.payment_id}",
                accept_partial=action == RecoveryAction.PARTIAL_PAYMENT,
                reminder_enable=False,
            )
        except (httpx.HTTPError, RuntimeError, ValueError):
            self.repository.complete_action(action_id, status="failed")
            self.repository.update_decision_execution_status(decision_id, "failed")
            failure = {**result, "execution_status": "failed"}
            self.repository.complete_event(event_id, "FAILED", failure)
            raise

        self.repository.complete_action(
            action_id,
            status="executed",
            external_action_id=link.get("id"),
            external_action_url=link.get("short_url"),
            increment_attempt=True,
            increment_contact=action in CONTACT_ACTIONS,
        )
        self.repository.update_decision_execution_status(decision_id, "executed")
        result.update(
            execution_status="executed",
            payment_link_id=link.get("id"),
            payment_link_url=link.get("short_url"),
        )
        self.repository.complete_event(event_id, "PROCESSED", result)
        return result

    @staticmethod
    def _execution_status(
        mode: Mode,
        policy_decision: str,
        action: RecoveryAction,
        execute_razorpay_actions: bool,
    ) -> str:
        if mode == "shadow":
            return "shadow_logged"
        if mode == "assisted" or policy_decision == "REQUIRE_APPROVAL":
            return "awaiting_human_approval"
        if policy_decision == "BLOCK":
            return "blocked"
        if not execute_razorpay_actions:
            return "execution_disabled"
        if action == RecoveryAction.NO_ACTION:
            return "no_action"
        if action not in LINK_ACTIONS:
            return "recommendation_only"
        return "pending_execution"

    @staticmethod
    def _context_from_failed_payment(event, case: dict) -> RecoveryContext:
        first_failed_at = case.get("first_failed_at")
        hours_since_failure = 0.0
        if first_failed_at is not None and event.created_at is not None:
            hours_since_failure = max(
                0.0,
                (event.created_at - first_failed_at) / 3600,
            )
        return RecoveryContext(
            case_id=case["case_id"],
            customer_id=case["customer_id"],
            amount_paise=case["amount_paise"],
            segment="NEW_ECOM",
            failure_reason=case["failure_reason"],
            payment_method=case["payment_method"],
            lifetime_value_paise=case["amount_paise"],
            tenure_days=0,
            historical_success_rate=0.70,
            prior_recovery_success_rate=0.40,
            attempts=case["attempts"],
            contacts_last_7d=case["contacts_last_7d"],
            hours_since_failure=hours_since_failure,
            opted_out=bool(case["opted_out"]),
            already_recovered=case["status"] == "RECOVERED",
        )
