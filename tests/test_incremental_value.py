import inspect

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.policies.incremental_value import IncrementalValuePolicy
from backend.app.simulator.benchmark import benchmark, multiseed_benchmark
from backend.app.simulator.environment import RecoveryGym
from backend.app.simulator.training import (
    generate_logged_history,
    train_incremental_value_policy,
)


def test_policy_module_has_no_simulator_truth_dependency():
    source = inspect.getsource(
        __import__(
            "backend.app.policies.incremental_value",
            fromlist=["IncrementalValuePolicy"],
        )
    )

    assert "RecoveryGym" not in source
    assert "success_probability" not in source
    assert "latent_recovery_rank" not in source
    assert "CounterfactualEvaluator" not in source


def test_logged_history_has_one_permitted_observed_action_per_case():
    history = generate_logged_history(events=60, seed=91)
    environment = RecoveryGym(seed=91)

    assert len(history) == 60
    assert len({context.case_id for context, _, _ in history}) == 60
    for context, action, outcome in history:
        assert action in environment.safety.allowed_actions(context)
        assert outcome.outcome_observed is True


def test_only_selected_action_model_learns_from_an_outcome():
    environment = RecoveryGym(seed=4)
    context = environment.sample_context(0)
    action = environment.safety.allowed_actions(context)[0]
    policy = IncrementalValuePolicy()
    before = {
        candidate: model.observations
        for candidate, model in policy.models.items()
    }

    outcome = environment.step(context, action)
    policy.update_observed_outcome(context, action, outcome)

    for candidate, model in policy.models.items():
        expected = before[candidate] + int(candidate == action)
        assert model.observations == expected


def test_policy_selects_highest_expected_value_permitted_action():
    environment = RecoveryGym(seed=8)
    context = environment.sample_context(2)
    allowed = environment.safety.allowed_actions(context)
    policy = train_incremental_value_policy(history_events=600, epochs=2)

    selected = policy.select_action(context, allowed_actions=allowed)
    values = {
        action: policy.estimate_action(context, action).expected_net_value_paise
        for action in allowed
    }

    assert selected in allowed
    assert values[selected] == max(values.values())


def test_benchmark_exposes_estimates_and_leakage_declarations():
    result = benchmark(events=30, seed=3)
    learner = result["incremental_value"]
    metrics = learner["estimated_decision_metrics"]

    assert metrics["estimates_from_observable_features_only"] is True
    assert metrics["pre_evaluation_training"]["uses_simulator_probabilities"] is False
    assert metrics["pre_evaluation_training"][
        "uses_counterfactual_outcomes_for_training"
    ] is False
    assert learner["observed_outcomes"] == 30


def test_multiseed_report_has_incremental_value_confidence_interval():
    report = multiseed_benchmark(events=20, seeds=3)
    comparison = report["paired_policy_comparison"]

    assert comparison[
        "incremental_value_additional_recovered_revenue_rupees_vs_rules_ci95"
    ]["n"] == 3
    assert comparison["incremental_value_directional_claim"] in {
        "INCONCLUSIVE",
        "INCREMENTAL_VALUE_AHEAD",
        "RULES_AHEAD",
    }


def test_decision_endpoint_returns_permitted_observable_estimates():
    with TestClient(app) as client:
        response = client.get("/api/simulations/decision?seed=42&event_index=0")

    assert response.status_code == 200
    body = response.json()
    assert body["selected_action"] in body["permitted_action_estimates"]
    assert body["estimate_boundary"]["observable_features_only"] is True
    assert body["estimate_boundary"]["simulator_probabilities_visible"] is False
    for estimate in body["permitted_action_estimates"].values():
        assert 0 <= estimate["natural_recovery_probability"] <= 1
        assert 0 <= estimate["action_recovery_probability"] <= 1
