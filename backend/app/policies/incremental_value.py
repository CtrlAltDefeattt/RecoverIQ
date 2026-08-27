from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np

from backend.app.domain.economics import intervention_cost_paise
from backend.app.domain.models import (
    RecoveryAction,
    RecoveryContext,
    RecoveryOutcome,
)
from backend.app.policies.base import RecoveryPolicy


def observable_features(ctx: RecoveryContext) -> np.ndarray:
    """Features available to a real decision service; no simulator truth."""
    derived = [
        1.0 if ctx.amount_paise >= 700_000 else 0.0,
        1.0 if ctx.attempts >= 2 else 0.0,
        1.0 if ctx.contacts_last_7d >= 2 else 0.0,
        1.0 if ctx.hours_since_failure >= 12 else 0.0,
        math.log1p(ctx.amount_paise) / math.log1p(5_000_000),
    ]
    return np.asarray(ctx.features() + derived, dtype=float)


@dataclass(frozen=True)
class ActionValueEstimate:
    action: str
    natural_recovery_probability: float
    action_recovery_probability: float
    estimated_probability_uplift: float
    intervention_cost_paise: int
    expected_net_value_paise: float
    expected_incremental_value_paise: float
    training_observations: int

    def to_dict(self) -> dict:
        return asdict(self)


class OnlineLogisticResponseModel:
    def __init__(
        self,
        dimensions: int,
        prior_probability: float = 0.40,
        learning_rate: float = 0.08,
        l2: float = 0.0005,
    ):
        self.weights = np.zeros(dimensions, dtype=float)
        self.weights[0] = math.log(prior_probability / (1 - prior_probability))
        self.learning_rate = learning_rate
        self.l2 = l2
        self.observations = 0

    def predict(self, features: np.ndarray) -> float:
        logit = float(np.clip(self.weights @ features, -20.0, 20.0))
        return 1.0 / (1.0 + math.exp(-logit))

    def update(self, features: np.ndarray, recovered: bool) -> None:
        probability = self.predict(features)
        error = float(recovered) - probability
        step = self.learning_rate / math.sqrt(1 + self.observations / 250)
        regularization = self.l2 * self.weights
        regularization[0] = 0.0
        self.weights += step * (error * features - regularization)
        self.observations += 1


class IncrementalValuePolicy(RecoveryPolicy):
    """Outcome learner that selects the largest estimated permitted net value."""

    model_version = "observable-logistic-tlearner-v1"

    def __init__(self):
        dimensions = len(observable_features(_feature_shape_context()))
        self.models = {
            action: OnlineLogisticResponseModel(dimensions)
            for action in RecoveryAction
        }
        self.online_updates = 0

    def predict_probability(
        self,
        ctx: RecoveryContext,
        action: RecoveryAction,
    ) -> float:
        return self.models[action].predict(observable_features(ctx))

    def estimate_action(
        self,
        ctx: RecoveryContext,
        action: RecoveryAction,
    ) -> ActionValueEstimate:
        natural_probability = self.predict_probability(
            ctx,
            RecoveryAction.NO_ACTION,
        )
        action_probability = self.predict_probability(ctx, action)
        cost = intervention_cost_paise(ctx, action)
        expected_value = action_probability * ctx.amount_paise - cost
        natural_value = natural_probability * ctx.amount_paise
        return ActionValueEstimate(
            action=action.value,
            natural_recovery_probability=natural_probability,
            action_recovery_probability=action_probability,
            estimated_probability_uplift=action_probability
            - natural_probability,
            intervention_cost_paise=cost,
            expected_net_value_paise=expected_value,
            expected_incremental_value_paise=expected_value - natural_value,
            training_observations=self.models[action].observations,
        )

    def estimates_for_actions(
        self,
        ctx: RecoveryContext,
        allowed_actions: list[RecoveryAction],
    ) -> dict[str, dict]:
        return {
            action.value: self.estimate_action(ctx, action).to_dict()
            for action in allowed_actions
        }

    def select_action(
        self,
        ctx: RecoveryContext,
        allowed_actions: list[RecoveryAction] | None = None,
    ) -> RecoveryAction:
        candidates = (
            allowed_actions
            if allowed_actions is not None
            else list(RecoveryAction)
        )
        if not candidates:
            raise ValueError("No eligible recovery actions")
        estimates = {
            action: self.estimate_action(ctx, action) for action in candidates
        }
        return max(
            candidates,
            key=lambda action: (
                estimates[action].expected_net_value_paise,
                -list(RecoveryAction).index(action),
            ),
        )

    def update(
        self,
        ctx: RecoveryContext,
        action: RecoveryAction,
        reward_paise: int,
    ) -> None:
        # A failed intervention has a negative action-cost reward; every
        # recovered payment in the current bounded environment remains positive.
        recovered = reward_paise > 0
        self.models[action].update(observable_features(ctx), recovered)
        self.online_updates += 1

    def update_observed_outcome(
        self,
        ctx: RecoveryContext,
        action: RecoveryAction,
        outcome: RecoveryOutcome,
    ) -> None:
        self.models[action].update(observable_features(ctx), outcome.recovered)
        self.online_updates += 1

    def training_summary(self) -> dict:
        return {
            "model_version": self.model_version,
            "observable_feature_count": len(
                observable_features(_feature_shape_context())
            ),
            "observations_by_action": {
                action.value: model.observations
                for action, model in self.models.items()
            },
            "online_updates": self.online_updates,
            "uses_simulator_probabilities": False,
            "uses_counterfactual_outcomes_for_training": False,
        }


def _feature_shape_context() -> RecoveryContext:
    return RecoveryContext(
        case_id="shape",
        customer_id="shape",
        amount_paise=100,
        segment="NEW_ECOM",
        failure_reason="BANK_DECLINED",
        payment_method="upi",
        lifetime_value_paise=100,
        tenure_days=0,
        historical_success_rate=0.5,
        prior_recovery_success_rate=0.5,
        attempts=0,
        contacts_last_7d=0,
        hours_since_failure=0,
    )
