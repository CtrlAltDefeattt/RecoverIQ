from dataclasses import asdict
from functools import lru_cache

from fastapi import APIRouter, Query

from backend.app.simulator.benchmark import benchmark
from backend.app.simulator.environment import RecoveryGym
from backend.app.simulator.training import train_incremental_value_policy

router = APIRouter(prefix="/api/simulations", tags=["simulations"])


@router.post("/run")
def run_simulation(
    events: int = Query(default=1000, ge=100, le=100000),
    seed: int = Query(default=42),
):
    return benchmark(events=events, seed=seed)


@lru_cache
def _demo_incremental_value_policy():
    return train_incremental_value_policy()


@router.get("/decision")
def explain_simulated_decision(
    seed: int = Query(default=42),
    event_index: int = Query(default=0, ge=0, le=1_000_000),
):
    environment = RecoveryGym(seed=seed)
    context = environment.sample_context(event_index)
    allowed_actions = environment.safety.allowed_actions(context)
    policy = _demo_incremental_value_policy()
    selected_action = policy.select_action(
        context,
        allowed_actions=allowed_actions,
    )

    return {
        "context": asdict(context),
        "selected_action": selected_action.value,
        "selection_objective": "MAX_EXPECTED_NET_VALUE",
        "estimate_boundary": {
            "observable_features_only": True,
            "simulator_probabilities_visible": False,
            "counterfactual_outcomes_visible": False,
        },
        "permitted_action_estimates": policy.estimates_for_actions(
            context,
            allowed_actions,
        ),
        "model": policy.training_summary(),
    }
