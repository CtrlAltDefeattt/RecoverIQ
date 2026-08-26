from __future__ import annotations

from typing import Literal

from backend.app.adapters.razorpay import RazorpayAdapter
from backend.app.domain.events import (
    UnsupportedWebhookEvent,
    map_failure_reason,
    normalize_payment_event,
)
from backend.app.domain.models import RecoveryAction, RecoveryContext
from backend.app.policies.baselines import RuleBasedPolicy
from backend.app.safety.engine import SafetyEngine


Mode = Literal["shadow", "assisted", "autonomous"]
LINK_ACTIONS = {
    RecoveryAction.PAYMENT_LINK,
    RecoveryAction.ALT_PAYMENT,
    RecoveryAction.PARTIAL_PAYMENT,
}


class RazorpayIntegrationService:
    """Day-2 in-memory webhook-to-decision integration.

    Durable event and case storage replaces these collections on the persistence
    milestone. The state transition behavior is already explicit and tested.
    """

    def __init__(
        self,
        policy: RuleBasedPolicy | None = None,
        safety: SafetyEngine | None = None,
    ):
        self.policy = policy or RuleBasedPolicy()
        self.safety = safety or SafetyEngine()
        self.processed_event_ids: set[str] = set()
        self.payment_status: dict[str, str] = {}

    def reset(self) -> None:
        self.processed_event_ids.clear()
        self.payment_status.clear()

    async def process(
        self,
        event_id: str,
        payload: dict,
        *,
        mode: Mode,
        execute_razorpay_actions: bool,
        adapter: RazorpayAdapter,
    ) -> dict:
        if event_id in self.processed_event_ids:
            return {"status": "duplicate_ignored", "event_id": event_id}

        try:
            event = normalize_payment_event(event_id, payload)
        except UnsupportedWebhookEvent as exc:
            self.processed_event_ids.add(event_id)
            return {
                "status": "unsupported_event_ignored",
                "event_id": event_id,
                "event": str(exc),
            }

        self.processed_event_ids.add(event_id)

        if event.event_type == "payment.captured":
            self.payment_status[event.payment_id] = "RECOVERED"
            return {
                "status": "case_closed",
                "event_id": event_id,
                "event": event.event_type,
                "payment_id": event.payment_id,
                "recovered_amount_paise": event.amount_paise,
            }

        if self.payment_status.get(event.payment_id) == "RECOVERED":
            return {
                "status": "stale_failure_ignored",
                "event_id": event_id,
                "event": event.event_type,
                "payment_id": event.payment_id,
                "reason": "PAYMENT_ALREADY_CAPTURED",
            }

        context = self._context_from_failed_payment(event)
        reviewable_actions = self.safety.reviewable_actions(context)
        action = self.policy.select_action(
            context,
            allowed_actions=reviewable_actions,
        )
        safety = self.safety.evaluate(context, action)
        self.payment_status[event.payment_id] = "AT_RISK"

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
            "execution_status": "not_executed",
        }

        if mode == "shadow":
            result["execution_status"] = "shadow_logged"
            return result
        if mode == "assisted" or safety.decision.value == "REQUIRE_APPROVAL":
            result["execution_status"] = "awaiting_human_approval"
            return result
        if safety.decision.value == "BLOCK":
            result["execution_status"] = "blocked"
            return result
        if not execute_razorpay_actions:
            result["execution_status"] = "execution_disabled"
            return result
        if action == RecoveryAction.NO_ACTION:
            result["execution_status"] = "no_action"
            return result
        if action not in LINK_ACTIONS:
            result["execution_status"] = "recommendation_only"
            return result

        link = await adapter.create_payment_link(
            amount_paise=event.amount_paise,
            reference_id=f"recover_{event.payment_id}"[:40],
            description=f"Recover failed payment {event.payment_id}",
            accept_partial=action == RecoveryAction.PARTIAL_PAYMENT,
            reminder_enable=False,
        )
        result.update(
            execution_status="executed",
            payment_link_id=link.get("id"),
            payment_link_url=link.get("short_url"),
        )
        return result

    @staticmethod
    def _context_from_failed_payment(event) -> RecoveryContext:
        # Conservative cold-start defaults until merchant history is persisted.
        return RecoveryContext(
            case_id=f"case_{event.payment_id}",
            customer_id=event.customer_email
            or event.customer_contact
            or event.payment_id,
            amount_paise=event.amount_paise,
            segment="NEW_ECOM",
            failure_reason=map_failure_reason(event),
            payment_method=event.payment_method,
            lifetime_value_paise=event.amount_paise,
            tenure_days=0,
            historical_success_rate=0.70,
            prior_recovery_success_rate=0.40,
            attempts=0,
            contacts_last_7d=0,
            hours_since_failure=0,
        )
