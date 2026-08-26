from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from statistics import mean, stdev

from backend.app.domain.models import RecoveryAction, RecoveryContext, RecoveryOutcome
from backend.app.simulator.environment import RecoveryGym


@dataclass(frozen=True)
class PotentialOutcome:
    action: str
    success_probability: float
    recovered: bool
    recovered_amount_paise: int
    intervention_cost_paise: int
    realized_value_paise: int
    expected_value_paise: float


@dataclass(frozen=True)
class EvaluationSnapshot:
    natural_recovery_probability: float
    selected_success_probability: float
    probability_uplift: float
    natural_recovered_amount_paise: int
    selected_recovered_amount_paise: int
    realized_incremental_revenue_paise: int
    expected_incremental_value_paise: float
    realized_incremental_value_paise: int
    oracle_action: str
    oracle_value_paise: int
    oracle_regret_paise: int

    def to_dict(self) -> dict:
        return asdict(self)


class CounterfactualEvaluator:
    """Evaluator-only access to synthetic potential outcomes.

    A policy selects an action before this class is called. The evaluator then
    reveals outcomes for all autonomously permitted actions solely to score the
    decision; none of these counterfactuals are passed to policy.update().
    """

    def __init__(self, environment: RecoveryGym):
        self.environment = environment

    def potential_outcomes(
        self,
        ctx: RecoveryContext,
    ) -> dict[RecoveryAction, PotentialOutcome]:
        potentials = {}
        for action in self.environment.safety.allowed_actions(ctx):
            probability = self.environment.success_probability(ctx, action)
            recovered = self.environment.latent_recovery_rank(ctx) < probability
            recovered_amount = ctx.amount_paise if recovered else 0
            cost = self.environment.intervention_cost_paise(ctx, action)
            potentials[action] = PotentialOutcome(
                action=action.value,
                success_probability=probability,
                recovered=recovered,
                recovered_amount_paise=recovered_amount,
                intervention_cost_paise=cost,
                realized_value_paise=recovered_amount - cost,
                expected_value_paise=probability * ctx.amount_paise - cost,
            )
        return potentials

    def evaluate(
        self,
        ctx: RecoveryContext,
        selected_action: RecoveryAction,
        selected_outcome: RecoveryOutcome,
    ) -> EvaluationSnapshot:
        potentials = self.potential_outcomes(ctx)
        if selected_action not in potentials:
            raise ValueError("Selected action is not autonomously permitted")
        if not selected_outcome.outcome_observed:
            raise ValueError("Counterfactual scoring requires an observed outcome")

        selected = potentials[selected_action]
        natural = potentials[RecoveryAction.NO_ACTION]
        if selected.realized_value_paise != selected_outcome.reward_paise:
            raise ValueError("Selected outcome does not match evaluator potential")

        oracle_action, oracle = max(
            potentials.items(),
            key=lambda item: (item[1].realized_value_paise, -list(RecoveryAction).index(item[0])),
        )
        regret = oracle.realized_value_paise - selected.realized_value_paise

        return EvaluationSnapshot(
            natural_recovery_probability=natural.success_probability,
            selected_success_probability=selected.success_probability,
            probability_uplift=selected.success_probability
            - natural.success_probability,
            natural_recovered_amount_paise=natural.recovered_amount_paise,
            selected_recovered_amount_paise=selected.recovered_amount_paise,
            realized_incremental_revenue_paise=selected.recovered_amount_paise
            - natural.recovered_amount_paise,
            expected_incremental_value_paise=selected.expected_value_paise
            - natural.expected_value_paise,
            realized_incremental_value_paise=selected.realized_value_paise
            - natural.realized_value_paise,
            oracle_action=oracle_action.value,
            oracle_value_paise=oracle.realized_value_paise,
            oracle_regret_paise=max(0, regret),
        )


_T_CRITICAL_95 = {
    1: 12.706,
    2: 4.303,
    3: 3.182,
    4: 2.776,
    5: 2.571,
    6: 2.447,
    7: 2.365,
    8: 2.306,
    9: 2.262,
    10: 2.228,
    11: 2.201,
    12: 2.179,
    13: 2.160,
    14: 2.145,
    15: 2.131,
    16: 2.120,
    17: 2.110,
    18: 2.101,
    19: 2.093,
    20: 2.086,
    21: 2.080,
    22: 2.074,
    23: 2.069,
    24: 2.064,
    25: 2.060,
    26: 2.056,
    27: 2.052,
    28: 2.048,
    29: 2.045,
    30: 2.042,
}


def confidence_interval_95(values: list[float]) -> dict:
    if not values:
        raise ValueError("At least one value is required")
    center = mean(values)
    if len(values) == 1:
        return {
            "mean": round(center, 3),
            "lower": None,
            "upper": None,
            "sample_std": None,
            "n": 1,
        }

    sample_std = stdev(values)
    critical = _T_CRITICAL_95.get(len(values) - 1, 1.96)
    margin = critical * sample_std / math.sqrt(len(values))
    return {
        "mean": round(center, 3),
        "lower": round(center - margin, 3),
        "upper": round(center + margin, 3),
        "sample_std": round(sample_std, 3),
        "n": len(values),
    }


def directional_claim(interval: dict) -> str:
    lower = interval["lower"]
    upper = interval["upper"]
    if lower is None or upper is None or lower <= 0 <= upper:
        return "INCONCLUSIVE"
    return "LINUCB_AHEAD" if lower > 0 else "RULES_AHEAD"
