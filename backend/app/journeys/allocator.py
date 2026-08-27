from __future__ import annotations

from dataclasses import dataclass

from backend.app.domain.models import RecoveryAction, RecoveryContext
from backend.app.policies.incremental_value import IncrementalValuePolicy
from backend.app.safety.engine import SafetyEngine


@dataclass(frozen=True)
class AllocationCandidate:
    case_id: str
    segment: str
    action: RecoveryAction
    action_cost_paise: int
    expected_incremental_value_paise: float
    priority_score: float
    estimate: dict

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "segment": self.segment,
            "action": self.action.value,
            "action_cost_paise": self.action_cost_paise,
            "expected_incremental_value_paise": round(
                self.expected_incremental_value_paise, 3
            ),
            "priority_score": round(self.priority_score, 6),
            "estimate": self.estimate,
        }


class BatchBudgetAllocator:
    def __init__(
        self,
        policy: IncrementalValuePolicy,
        safety: SafetyEngine | None = None,
    ):
        self.policy = policy
        self.safety = safety or SafetyEngine()

    def allocate(
        self,
        contexts: list[RecoveryContext],
        budget_paise: int,
        max_actions: int,
    ) -> dict:
        if budget_paise < 0:
            raise ValueError("budget_paise cannot be negative")
        if max_actions < 0:
            raise ValueError("max_actions cannot be negative")

        candidates = []
        seen_case_ids = set()
        skipped = {
            "duplicate_case": 0,
            "no_positive_action": 0,
            "budget_or_action_cap": 0,
        }

        for context in contexts:
            if context.case_id in seen_case_ids:
                skipped["duplicate_case"] += 1
                continue
            seen_case_ids.add(context.case_id)
            allowed = self.safety.allowed_actions(context)
            action = self.policy.select_action(context, allowed_actions=allowed)
            estimate = self.policy.estimate_action(context, action)
            if (
                action == RecoveryAction.NO_ACTION
                or estimate.expected_incremental_value_paise <= 0
            ):
                skipped["no_positive_action"] += 1
                continue
            cost = estimate.intervention_cost_paise
            candidates.append(
                AllocationCandidate(
                    case_id=context.case_id,
                    segment=context.segment,
                    action=action,
                    action_cost_paise=cost,
                    expected_incremental_value_paise=(
                        estimate.expected_incremental_value_paise
                    ),
                    priority_score=(
                        estimate.expected_incremental_value_paise / max(cost, 1)
                    ),
                    estimate=estimate.to_dict(),
                )
            )

        candidates.sort(
            key=lambda candidate: (
                -candidate.priority_score,
                -candidate.expected_incremental_value_paise,
                candidate.case_id,
            )
        )
        selected = []
        spent = 0
        segment_counts = {}
        for candidate in candidates:
            if len(selected) >= max_actions:
                skipped["budget_or_action_cap"] += 1
                continue
            if spent + candidate.action_cost_paise > budget_paise:
                skipped["budget_or_action_cap"] += 1
                continue
            selected.append(candidate)
            spent += candidate.action_cost_paise
            segment_counts[candidate.segment] = (
                segment_counts.get(candidate.segment, 0) + 1
            )

        return {
            "budget_paise": budget_paise,
            "spent_paise": spent,
            "remaining_paise": budget_paise - spent,
            "max_actions": max_actions,
            "selected_count": len(selected),
            "candidate_count": len(candidates),
            "expected_incremental_value_paise": round(
                sum(item.expected_incremental_value_paise for item in selected),
                3,
            ),
            "segment_counts": segment_counts,
            "skipped": skipped,
            "selected": [candidate.to_dict() for candidate in selected],
        }
