from __future__ import annotations

from dataclasses import replace

from backend.app.domain.models import (
    PolicyDecision,
    RecoveryAction,
    RecoveryContext,
    RecoveryOutcome,
)
from backend.app.journeys.models import (
    InterventionRecord,
    JourneyCommand,
    JourneyDecision,
    JourneyState,
    JourneyStatus,
)
from backend.app.policies.incremental_value import IncrementalValuePolicy
from backend.app.safety.engine import CONTACT_ACTIONS, SafetyEngine


class JourneyOrchestrator:
    def __init__(
        self,
        policy: IncrementalValuePolicy,
        safety: SafetyEngine | None = None,
    ):
        self.policy = policy
        self.safety = safety or SafetyEngine()

    def effective_context(
        self,
        state: JourneyState,
        now_hours: float,
    ) -> RecoveryContext:
        contact_count = sum(
            record.action in CONTACT_ACTIONS for record in state.interventions
        )
        return replace(
            state.context,
            attempts=state.context.attempts + len(state.interventions),
            contacts_last_7d=state.context.contacts_last_7d + contact_count,
            hours_since_failure=max(state.context.hours_since_failure, now_hours),
            already_recovered=state.status == JourneyStatus.RECOVERED,
        )

    def next_decision(
        self,
        state: JourneyState,
        now_hours: float,
    ) -> JourneyDecision:
        if state.terminal:
            return JourneyDecision(
                command=JourneyCommand.STOP,
                reason=f"TERMINAL_{state.status.value}",
            )

        if len(state.interventions) >= state.max_interventions:
            state.status = JourneyStatus.EXHAUSTED
            state.stop_reason = "MAX_INTERVENTIONS_REACHED"
            return JourneyDecision(
                command=JourneyCommand.STOP,
                reason=state.stop_reason,
            )

        last_at = state.last_intervention_at_hours
        if last_at is not None:
            elapsed = now_hours - last_at
            if elapsed + 1e-9 < state.min_interval_hours:
                state.status = JourneyStatus.WAITING
                return JourneyDecision(
                    command=JourneyCommand.WAIT,
                    reason="INTERVENTION_COOLDOWN",
                    retry_after_hours=round(
                        state.min_interval_hours - elapsed,
                        3,
                    ),
                )

        state.status = JourneyStatus.OPEN
        context = self.effective_context(state, now_hours)
        used_actions = {record.action for record in state.interventions}
        allowed_actions = [
            action
            for action in self.safety.allowed_actions(context)
            if action == RecoveryAction.NO_ACTION or action not in used_actions
        ]
        if not allowed_actions:
            state.status = JourneyStatus.STOPPED
            state.stop_reason = "NO_PERMITTED_ACTION"
            return JourneyDecision(JourneyCommand.STOP, state.stop_reason)

        allowed_action = self.policy.select_action(
            context,
            allowed_actions=allowed_actions,
        )
        allowed_estimate = self.policy.estimate_action(
            context,
            allowed_action,
        )

        reviewable_actions = [
            action
            for action in self.safety.reviewable_actions(context)
            if action != RecoveryAction.NO_ACTION and action not in used_actions
        ]
        if reviewable_actions:
            review_action = self.policy.select_action(
                context,
                allowed_actions=reviewable_actions,
            )
            review_estimate = self.policy.estimate_action(context, review_action)
            review_safety = self.safety.evaluate(context, review_action)
            if (
                review_safety.decision == PolicyDecision.REQUIRE_APPROVAL
                and review_estimate.expected_incremental_value_paise > 0
                and review_estimate.expected_net_value_paise
                > allowed_estimate.expected_net_value_paise
            ):
                state.status = JourneyStatus.ESCALATED
                state.stop_reason = review_safety.reason
                return JourneyDecision(
                    command=JourneyCommand.ESCALATE,
                    reason=review_safety.reason,
                    action=review_action,
                    estimate=review_estimate.to_dict(),
                )

        if (
            allowed_action == RecoveryAction.NO_ACTION
            or allowed_estimate.expected_incremental_value_paise <= 0
        ):
            state.status = JourneyStatus.STOPPED
            state.stop_reason = "NO_POSITIVE_INCREMENTAL_VALUE"
            return JourneyDecision(
                command=JourneyCommand.STOP,
                reason=state.stop_reason,
                estimate=allowed_estimate.to_dict(),
            )

        return JourneyDecision(
            command=JourneyCommand.EXECUTE,
            reason="POSITIVE_PERMITTED_INCREMENTAL_VALUE",
            action=allowed_action,
            estimate=allowed_estimate.to_dict(),
        )

    def apply_outcome(
        self,
        state: JourneyState,
        decision: JourneyDecision,
        outcome: RecoveryOutcome,
        executed_at_hours: float,
    ) -> None:
        if decision.command != JourneyCommand.EXECUTE or decision.action is None:
            raise ValueError("Only an EXECUTE decision can receive an outcome")
        if state.terminal:
            raise ValueError("Cannot apply an outcome to a terminal journey")
        if outcome.action != decision.action or not outcome.outcome_observed:
            raise ValueError("Outcome must be observed for the selected action")

        learning_context = self.effective_context(state, executed_at_hours)
        state.interventions.append(
            InterventionRecord(
                sequence=len(state.interventions) + 1,
                action=decision.action,
                executed_at_hours=executed_at_hours,
                recovered=outcome.recovered,
                recovered_amount_paise=outcome.recovered_amount_paise,
                reward_paise=outcome.reward_paise,
                estimate=decision.estimate or {},
            )
        )
        self.policy.update_observed_outcome(
            learning_context,
            decision.action,
            outcome,
        )

        if outcome.recovered:
            state.status = JourneyStatus.RECOVERED
            state.stop_reason = "PAYMENT_RECOVERED"
        elif len(state.interventions) >= state.max_interventions:
            state.status = JourneyStatus.EXHAUSTED
            state.stop_reason = "MAX_INTERVENTIONS_REACHED"
        else:
            state.status = JourneyStatus.OPEN
