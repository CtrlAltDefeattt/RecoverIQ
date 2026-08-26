from backend.app.domain.models import RecoveryAction
from backend.app.simulator.benchmark import benchmark, multiseed_benchmark
from backend.app.simulator.environment import RecoveryGym
from backend.app.simulator.evaluation import (
    CounterfactualEvaluator,
    confidence_interval_95,
    directional_claim,
)


def test_potential_outcomes_are_deterministic_and_paired():
    first_env = RecoveryGym(seed=17)
    second_env = RecoveryGym(seed=17)
    first_ctx = first_env.sample_context(9)
    second_ctx = second_env.sample_context(9)

    first = CounterfactualEvaluator(first_env).potential_outcomes(first_ctx)
    second = CounterfactualEvaluator(second_env).potential_outcomes(second_ctx)

    assert first == second
    ordered = sorted(first.values(), key=lambda outcome: outcome.success_probability)
    recovered_flags = [outcome.recovered for outcome in ordered]
    assert recovered_flags == sorted(recovered_flags)


def test_evaluator_scores_selected_action_without_negative_regret():
    env = RecoveryGym(seed=42)
    ctx = env.sample_context(3)
    action = RecoveryAction.PAYMENT_LINK
    assert action in env.safety.allowed_actions(ctx)

    observed = env.step(ctx, action)
    evaluation = CounterfactualEvaluator(env).evaluate(ctx, action, observed)

    assert evaluation.selected_recovered_amount_paise == observed.recovered_amount_paise
    assert evaluation.oracle_value_paise >= observed.reward_paise
    assert evaluation.oracle_regret_paise >= 0
    assert evaluation.probability_uplift >= 0


def test_benchmark_uses_identical_cases_for_every_policy():
    result = benchmark(events=40, seed=5)

    assert result["evaluation_contract"]["counterfactuals_visible_to_policy"] is False
    assert result["comparison"]["paired_case_count"] == 40
    assert result["synthetic_data_quality"]["passed"] is True
    assert result["random"]["revenue_at_risk_rupees"] == result["rules"][
        "revenue_at_risk_rupees"
    ]
    assert result["rules"]["natural_recovery"] == result["linucb"][
        "natural_recovery"
    ]
    assert sum(
        segment["events"] for segment in result["rules"]["segment_analysis"].values()
    ) == 40
    assert sum(
        action["events"] for action in result["rules"]["action_analysis"].values()
    ) == 40


def test_confidence_interval_and_claim_guardrail():
    inconclusive = confidence_interval_95([1.0, 2.0, 3.0])
    positive = confidence_interval_95([10.0, 11.0, 12.0])

    assert directional_claim(inconclusive) == "INCONCLUSIVE"
    assert directional_claim(positive) == "LINUCB_AHEAD"
    assert confidence_interval_95([4.0])["lower"] is None


def test_multiseed_report_includes_paired_confidence_intervals():
    report = multiseed_benchmark(events=20, seeds=3)
    comparison = report["paired_policy_comparison"]

    assert report["seed_count"] == 3
    assert len(report["runs"]) == 3
    assert comparison[
        "linucb_additional_recovered_revenue_rupees_vs_rules_ci95"
    ]["n"] == 3
    assert comparison["directional_claim"] in {
        "INCONCLUSIVE",
        "LINUCB_AHEAD",
        "RULES_AHEAD",
    }
