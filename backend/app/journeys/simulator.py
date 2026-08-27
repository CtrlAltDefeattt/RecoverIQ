from __future__ import annotations

from backend.app.domain.models import RecoveryContext
from backend.app.journeys.models import JourneyCommand, JourneyState
from backend.app.journeys.orchestrator import JourneyOrchestrator
from backend.app.policies.incremental_value import IncrementalValuePolicy
from backend.app.simulator.environment import RecoveryGym


def simulate_journey(
    context: RecoveryContext,
    policy: IncrementalValuePolicy,
    environment: RecoveryGym,
    *,
    max_interventions: int = 2,
    min_interval_hours: float = 24.0,
) -> dict:
    state = JourneyState(
        journey_id=f"journey_{context.case_id}",
        context=context,
        max_interventions=max_interventions,
        min_interval_hours=min_interval_hours,
    )
    orchestrator = JourneyOrchestrator(policy, environment.safety)
    now_hours = context.hours_since_failure
    timeline = []

    for _ in range(max_interventions * 2 + 3):
        decision = orchestrator.next_decision(state, now_hours)
        entry = {"at_hours": round(now_hours, 3), **decision.to_dict()}
        timeline.append(entry)

        if decision.command == JourneyCommand.WAIT:
            now_hours += decision.retry_after_hours or 0
            continue
        if decision.command != JourneyCommand.EXECUTE:
            break

        effective_context = orchestrator.effective_context(state, now_hours)
        outcome = environment.step(effective_context, decision.action)
        orchestrator.apply_outcome(
            state,
            decision,
            outcome,
            executed_at_hours=now_hours,
        )
        entry["outcome"] = {
            "recovered": outcome.recovered,
            "recovered_amount_paise": outcome.recovered_amount_paise,
            "reward_paise": outcome.reward_paise,
        }
        if state.terminal:
            break
    else:
        raise RuntimeError("Journey did not reach a bounded terminal state")

    return {**state.to_dict(), "timeline": timeline}
