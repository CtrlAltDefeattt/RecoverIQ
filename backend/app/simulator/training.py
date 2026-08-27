from __future__ import annotations

import random

from backend.app.domain.models import (
    RecoveryAction,
    RecoveryContext,
    RecoveryOutcome,
)
from backend.app.policies.incremental_value import IncrementalValuePolicy
from backend.app.simulator.environment import RecoveryGym


LoggedOutcome = tuple[RecoveryContext, RecoveryAction, RecoveryOutcome]


def generate_logged_history(
    events: int = 6000,
    seed: int = 20260829,
) -> list[LoggedOutcome]:
    """Create one observed, safety-permitted action outcome per past case."""
    if events <= 0:
        raise ValueError("events must be positive")
    environment = RecoveryGym(seed=seed)
    action_offsets = {action: index for index, action in enumerate(RecoveryAction)}
    action_counts = {action: 0 for action in RecoveryAction}
    history = []

    for index in range(events):
        ctx = environment.sample_context(index)
        allowed = environment.safety.allowed_actions(ctx)
        # Deterministic rotating exploration provides coverage without reading
        # success probabilities or any unselected potential outcome.
        action = min(
            allowed,
            key=lambda candidate: (
                action_counts[candidate],
                action_offsets[candidate],
            ),
        )
        outcome = environment.step(ctx, action)
        if not outcome.outcome_observed:
            raise RuntimeError("Historical exploration selected an unobserved action")
        history.append((ctx, action, outcome))
        action_counts[action] += 1
    return history


def train_incremental_value_policy(
    history_events: int = 6000,
    history_seed: int = 20260829,
    epochs: int = 4,
) -> IncrementalValuePolicy:
    if epochs <= 0:
        raise ValueError("epochs must be positive")
    history = generate_logged_history(history_events, history_seed)
    policy = IncrementalValuePolicy()
    rng = random.Random(history_seed)

    for _ in range(epochs):
        order = list(range(len(history)))
        rng.shuffle(order)
        for index in order:
            ctx, action, outcome = history[index]
            policy.update_observed_outcome(ctx, action, outcome)

    # Evaluation-time updates are counted separately from historical fitting.
    policy.online_updates = 0
    return policy
