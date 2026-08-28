from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from statistics import mean

from backend.app.policies.baselines import RandomPolicy, RuleBasedPolicy
from backend.app.policies.incremental_value import IncrementalValuePolicy
from backend.app.policies.linucb import LinUCBPolicy
from backend.app.simulator.environment import (
    FAILURES,
    METHODS,
    SEGMENTS,
    RecoveryGym,
)
from backend.app.simulator.evaluation import (
    CounterfactualEvaluator,
    confidence_interval_95,
    directional_claim,
)
from backend.app.simulator.training import train_incremental_value_policy


def _analysis_bucket() -> dict:
    return {
        "events": 0,
        "recovered_cases": 0,
        "recovered_revenue_paise": 0,
        "natural_recovery_revenue_paise": 0,
        "expected_incremental_value_paise": 0.0,
        "realized_incremental_value_paise": 0,
        "oracle_regret_paise": 0,
        "probability_uplift_sum": 0.0,
        "action_counts": {},
    }


def _finalize_analysis(buckets: dict[str, dict]) -> dict:
    report = {}
    for name, bucket in sorted(buckets.items()):
        events = bucket["events"]
        report[name] = {
            "events": events,
            "recovery_rate": round(bucket["recovered_cases"] / events, 4),
            "recovered_revenue_rupees": round(
                bucket["recovered_revenue_paise"] / 100, 2
            ),
            "natural_recovery_revenue_rupees": round(
                bucket["natural_recovery_revenue_paise"] / 100, 2
            ),
            "model_expected_incremental_value_rupees": round(
                bucket["expected_incremental_value_paise"] / 100, 2
            ),
            "realized_incremental_net_value_rupees": round(
                bucket["realized_incremental_value_paise"] / 100, 2
            ),
            "oracle_regret_rupees": round(
                bucket["oracle_regret_paise"] / 100, 2
            ),
            "mean_probability_uplift": round(
                bucket["probability_uplift_sum"] / events, 4
            ),
            "action_counts": bucket["action_counts"],
        }
    return report


def synthetic_data_quality(events: int, seed: int) -> dict:
    env = RecoveryGym(seed=seed)
    segment_counts = {segment: 0 for segment in SEGMENTS}
    invalid_amounts = 0
    invalid_categories = 0
    invalid_probabilities = 0
    minimum_amount = None
    maximum_amount = None

    for index in range(events):
        ctx = env.sample_context(index)
        segment_counts[ctx.segment] = segment_counts.get(ctx.segment, 0) + 1
        invalid_amounts += int(ctx.amount_paise <= 0)
        invalid_categories += int(
            ctx.segment not in SEGMENTS
            or ctx.failure_reason not in FAILURES
            or ctx.payment_method not in METHODS
        )
        minimum_amount = (
            ctx.amount_paise
            if minimum_amount is None
            else min(minimum_amount, ctx.amount_paise)
        )
        maximum_amount = (
            ctx.amount_paise
            if maximum_amount is None
            else max(maximum_amount, ctx.amount_paise)
        )
        invalid_probabilities += sum(
            not 0 <= env.success_probability(ctx, action) <= 1
            for action in env.safety.allowed_actions(ctx)
        )

    missing_segments = [
        segment for segment, count in segment_counts.items() if count == 0
    ]
    return {
        "passed": not (
            invalid_amounts or invalid_categories or invalid_probabilities
        ),
        "segment_counts": segment_counts,
        "missing_segments": missing_segments,
        "segment_coverage_ratio": round(
            (len(SEGMENTS) - len(missing_segments)) / len(SEGMENTS), 3
        ),
        "minimum_amount_paise": minimum_amount,
        "maximum_amount_paise": maximum_amount,
        "invalid_amounts": invalid_amounts,
        "invalid_categories": invalid_categories,
        "invalid_probabilities": invalid_probabilities,
    }


def run_policy(policy, events: int, seed: int) -> dict:
    if events <= 0:
        raise ValueError("events must be positive")

    env = RecoveryGym(seed=seed)
    evaluator = CounterfactualEvaluator(env)
    recovered_paise = 0
    at_risk_paise = 0
    rewards = []
    successes = 0
    blocks = 0
    approvals = 0
    no_actions = 0
    executed_actions = 0
    observed_outcomes = 0
    action_counts = {}
    oracle_action_counts = {}
    natural_expected_revenue_paise = 0.0
    natural_realized_revenue_paise = 0
    expected_incremental_value_paise = 0.0
    realized_incremental_revenue_paise = 0
    realized_incremental_value_paise = 0
    oracle_value_paise = 0
    oracle_regret_paise = 0
    probability_uplifts = []
    segment_buckets = {}
    action_buckets = {}
    estimation_count = 0
    predicted_natural_probability = 0.0
    predicted_action_probability = 0.0
    predicted_probability_uplift = 0.0
    predicted_incremental_value_paise = 0.0
    selected_probability_absolute_error = 0.0
    natural_probability_absolute_error = 0.0
    selected_brier_score = 0.0
    natural_brier_score = 0.0
    pre_evaluation_training = (
        policy.training_summary()
        if isinstance(policy, IncrementalValuePolicy)
        else None
    )

    for i in range(events):
        ctx = env.sample_context(i)
        at_risk_paise += ctx.amount_paise
        allowed_actions = env.safety.allowed_actions(ctx)
        action = policy.select_action(ctx, allowed_actions=allowed_actions)
        decision_estimate = (
            policy.estimate_action(ctx, action)
            if isinstance(policy, IncrementalValuePolicy)
            else None
        )
        action_counts[action.value] = action_counts.get(action.value, 0) + 1
        if action.value == "NO_ACTION":
            no_actions += 1

        outcome = env.step(ctx, action)

        if outcome.policy_decision.value == "BLOCK":
            blocks += 1
        elif outcome.policy_decision.value == "REQUIRE_APPROVAL":
            approvals += 1

        if outcome.executed:
            executed_actions += 1
        if outcome.outcome_observed:
            observed_outcomes += 1

        recovered_paise += outcome.recovered_amount_paise
        rewards.append(outcome.reward_paise)
        if outcome.recovered:
            successes += 1

        # Counterfactual outcomes are computed only after action selection and
        # never passed into the policy update below.
        evaluation = evaluator.evaluate(ctx, action, outcome)
        natural_expected_revenue_paise += (
            evaluation.natural_recovery_probability * ctx.amount_paise
        )
        natural_realized_revenue_paise += (
            evaluation.natural_recovered_amount_paise
        )
        expected_incremental_value_paise += (
            evaluation.expected_incremental_value_paise
        )
        realized_incremental_revenue_paise += (
            evaluation.realized_incremental_revenue_paise
        )
        realized_incremental_value_paise += (
            evaluation.realized_incremental_value_paise
        )
        oracle_value_paise += evaluation.oracle_value_paise
        oracle_regret_paise += evaluation.oracle_regret_paise
        probability_uplifts.append(evaluation.probability_uplift)
        oracle_action_counts[evaluation.oracle_action] = (
            oracle_action_counts.get(evaluation.oracle_action, 0) + 1
        )

        if decision_estimate is not None:
            estimation_count += 1
            predicted_natural_probability += (
                decision_estimate.natural_recovery_probability
            )
            predicted_action_probability += (
                decision_estimate.action_recovery_probability
            )
            predicted_probability_uplift += (
                decision_estimate.estimated_probability_uplift
            )
            predicted_incremental_value_paise += (
                decision_estimate.expected_incremental_value_paise
            )
            selected_probability_absolute_error += abs(
                decision_estimate.action_recovery_probability
                - evaluation.selected_success_probability
            )
            natural_probability_absolute_error += abs(
                decision_estimate.natural_recovery_probability
                - evaluation.natural_recovery_probability
            )
            selected_brier_score += (
                decision_estimate.action_recovery_probability
                - float(outcome.recovered)
            ) ** 2
            natural_brier_score += (
                decision_estimate.natural_recovery_probability
                - float(evaluation.natural_recovered_amount_paise > 0)
            ) ** 2

        for bucket_name, buckets in (
            (ctx.segment, segment_buckets),
            (action.value, action_buckets),
        ):
            bucket = buckets.setdefault(bucket_name, _analysis_bucket())
            bucket["events"] += 1
            bucket["recovered_cases"] += int(outcome.recovered)
            bucket["recovered_revenue_paise"] += outcome.recovered_amount_paise
            bucket["natural_recovery_revenue_paise"] += (
                evaluation.natural_recovered_amount_paise
            )
            bucket["expected_incremental_value_paise"] += (
                evaluation.expected_incremental_value_paise
            )
            bucket["realized_incremental_value_paise"] += (
                evaluation.realized_incremental_value_paise
            )
            bucket["oracle_regret_paise"] += evaluation.oracle_regret_paise
            bucket["probability_uplift_sum"] += evaluation.probability_uplift
            bucket["action_counts"][action.value] = (
                bucket["action_counts"].get(action.value, 0) + 1
            )

        # A blocked or approval-pending proposal was never executed, so zero is
        # not a customer outcome. Learning from it would incorrectly teach the
        # policy that the action failed.
        if outcome.outcome_observed:
            policy.update_observed_outcome(ctx, action, outcome)

    total_reward_paise = sum(rewards)
    result = {
        "events": events,
        "seed": seed,
        "revenue_at_risk_rupees": round(at_risk_paise / 100, 2),
        "recovered_revenue_rupees": round(recovered_paise / 100, 2),
        "total_net_value_rupees": round(total_reward_paise / 100, 2),
        "recovery_rate": round(successes / events, 4),
        "avg_reward_rupees": round(mean(rewards) / 100, 2),
        "natural_recovery": {
            "expected_revenue_rupees": round(
                natural_expected_revenue_paise / 100, 2
            ),
            "realized_revenue_rupees": round(
                natural_realized_revenue_paise / 100, 2
            ),
        },
        "intervention_effect": {
            "mean_probability_uplift": round(mean(probability_uplifts), 4),
            "model_expected_incremental_value_rupees": round(
                expected_incremental_value_paise / 100, 2
            ),
            "realized_incremental_revenue_rupees": round(
                realized_incremental_revenue_paise / 100, 2
            ),
            "realized_incremental_net_value_rupees": round(
                realized_incremental_value_paise / 100, 2
            ),
        },
        "oracle_evaluation": {
            "oracle_net_value_rupees": round(oracle_value_paise / 100, 2),
            "oracle_regret_rupees": round(oracle_regret_paise / 100, 2),
            "oracle_action_counts": oracle_action_counts,
        },
        "segment_analysis": _finalize_analysis(segment_buckets),
        "action_analysis": _finalize_analysis(action_buckets),
        "blocked_actions": blocks,
        "approval_required": approvals,
        "executed_actions": executed_actions,
        "observed_outcomes": observed_outcomes,
        "no_actions": no_actions,
        "action_counts": action_counts,
    }
    if estimation_count:
        result["estimated_decision_metrics"] = {
            "model_version": policy.model_version,
            "estimates_from_observable_features_only": True,
            "mean_estimated_natural_recovery_probability": round(
                predicted_natural_probability / estimation_count, 4
            ),
            "mean_estimated_selected_action_probability": round(
                predicted_action_probability / estimation_count, 4
            ),
            "mean_estimated_probability_uplift": round(
                predicted_probability_uplift / estimation_count, 4
            ),
            "total_estimated_incremental_value_rupees": round(
                predicted_incremental_value_paise / 100, 2
            ),
            "selected_probability_mae_against_evaluator": round(
                selected_probability_absolute_error / estimation_count, 4
            ),
            "natural_probability_mae_against_evaluator": round(
                natural_probability_absolute_error / estimation_count, 4
            ),
            "selected_outcome_brier_score": round(
                selected_brier_score / estimation_count, 4
            ),
            "natural_outcome_brier_score": round(
                natural_brier_score / estimation_count, 4
            ),
            "pre_evaluation_training": pre_evaluation_training,
            "post_evaluation_training": policy.training_summary(),
        }
    return result


def benchmark(events: int = 1000, seed: int = 42) -> dict:
    results = {
        "evaluation_contract": {
            "paired_cases": True,
            "paired_latent_outcomes": True,
            "counterfactuals_visible_to_policy": False,
            "oracle_scope": "AUTONOMOUSLY_PERMITTED_ACTIONS",
            "currency": "INR",
            "synthetic_only": True,
        },
        "synthetic_data_quality": synthetic_data_quality(events, seed),
        "random": run_policy(RandomPolicy(seed), events, seed),
        "rules": run_policy(RuleBasedPolicy(), events, seed),
        "linucb": run_policy(LinUCBPolicy(alpha=0.8), events, seed),
        "incremental_value": run_policy(
            train_incremental_value_policy(), events, seed
        ),
    }

    rules_recovered = results["rules"]["recovered_revenue_rupees"]
    linucb_recovered = results["linucb"]["recovered_revenue_rupees"]
    rules_value = results["rules"]["total_net_value_rupees"]
    linucb_value = results["linucb"]["total_net_value_rupees"]
    rules_regret = results["rules"]["oracle_evaluation"]["oracle_regret_rupees"]
    linucb_regret = results["linucb"]["oracle_evaluation"]["oracle_regret_rupees"]
    incremental_recovered = results["incremental_value"][
        "recovered_revenue_rupees"
    ]
    incremental_value = results["incremental_value"]["total_net_value_rupees"]
    incremental_regret = results["incremental_value"]["oracle_evaluation"][
        "oracle_regret_rupees"
    ]

    results["comparison"] = {
        "paired_case_count": events,
        "linucb_additional_simulated_rupees_vs_rules": round(
            linucb_recovered - rules_recovered, 2
        ),
        "linucb_additional_simulated_net_value_rupees_vs_rules": round(
            linucb_value - rules_value, 2
        ),
        "linucb_relative_gain_pct_vs_rules": round(
            ((linucb_recovered - rules_recovered) / rules_recovered * 100)
            if rules_recovered
            else 0.0,
            2,
        ),
        "linucb_oracle_regret_reduction_rupees_vs_rules": round(
            rules_regret - linucb_regret, 2
        ),
        "lower_regret_policy": "linucb"
        if linucb_regret < rules_regret
        else "rules",
        "incremental_value_additional_simulated_rupees_vs_rules": round(
            incremental_recovered - rules_recovered, 2
        ),
        "incremental_value_additional_net_value_rupees_vs_rules": round(
            incremental_value - rules_value, 2
        ),
        "incremental_value_relative_gain_pct_vs_rules": round(
            (
                (incremental_recovered - rules_recovered)
                / rules_recovered
                * 100
            )
            if rules_recovered
            else 0.0,
            2,
        ),
        "incremental_value_oracle_regret_reduction_rupees_vs_rules": round(
            rules_regret - incremental_regret, 2
        ),
    }
    return results


def _run_seed(arguments: tuple[int, int]) -> dict:
    events, seed = arguments
    return {"seed": seed, **benchmark(events, seed)}


def multiseed_benchmark(
    events: int = 10000,
    seeds: int = 10,
    workers: int = 1,
) -> dict:
    if seeds <= 0:
        raise ValueError("seeds must be positive")
    if workers <= 0:
        raise ValueError("workers must be positive")

    arguments = [(events, seed) for seed in range(seeds)]
    if workers == 1:
        runs = [_run_seed(item) for item in arguments]
    else:
        # executor.map preserves input order, so changing worker count cannot
        # change the committed paired-seed report.
        with ProcessPoolExecutor(max_workers=min(workers, seeds)) as executor:
            runs = list(executor.map(_run_seed, arguments))
    revenue_differences = [
        run["comparison"]["linucb_additional_simulated_rupees_vs_rules"]
        for run in runs
    ]
    value_differences = [
        run["comparison"][
            "linucb_additional_simulated_net_value_rupees_vs_rules"
        ]
        for run in runs
    ]
    regret_reductions = [
        run["comparison"]["linucb_oracle_regret_reduction_rupees_vs_rules"]
        for run in runs
    ]
    relative_gains = [
        run["comparison"]["linucb_relative_gain_pct_vs_rules"] for run in runs
    ]
    incremental_revenue_differences = [
        run["comparison"][
            "incremental_value_additional_simulated_rupees_vs_rules"
        ]
        for run in runs
    ]
    incremental_value_differences = [
        run["comparison"][
            "incremental_value_additional_net_value_rupees_vs_rules"
        ]
        for run in runs
    ]
    incremental_regret_reductions = [
        run["comparison"][
            "incremental_value_oracle_regret_reduction_rupees_vs_rules"
        ]
        for run in runs
    ]
    incremental_relative_gains = [
        run["comparison"]["incremental_value_relative_gain_pct_vs_rules"]
        for run in runs
    ]

    revenue_interval = confidence_interval_95(revenue_differences)
    incremental_revenue_interval = confidence_interval_95(
        incremental_revenue_differences
    )
    return {
        "evaluation_contract": runs[0]["evaluation_contract"],
        "events_per_seed": events,
        "seed_count": seeds,
        "paired_policy_comparison": {
            "linucb_additional_recovered_revenue_rupees_vs_rules_ci95": (
                revenue_interval
            ),
            "linucb_additional_net_value_rupees_vs_rules_ci95": (
                confidence_interval_95(value_differences)
            ),
            "linucb_oracle_regret_reduction_rupees_vs_rules_ci95": (
                confidence_interval_95(regret_reductions)
            ),
            "linucb_relative_recovered_revenue_gain_pct_ci95": (
                confidence_interval_95(relative_gains)
            ),
            "directional_claim": directional_claim(revenue_interval),
            "linucb_seed_win_rate": round(
                sum(value > 0 for value in revenue_differences) / seeds, 3
            ),
            "incremental_value_additional_recovered_revenue_rupees_vs_rules_ci95": (
                incremental_revenue_interval
            ),
            "incremental_value_additional_net_value_rupees_vs_rules_ci95": (
                confidence_interval_95(incremental_value_differences)
            ),
            "incremental_value_oracle_regret_reduction_rupees_vs_rules_ci95": (
                confidence_interval_95(incremental_regret_reductions)
            ),
            "incremental_value_relative_recovered_revenue_gain_pct_ci95": (
                confidence_interval_95(incremental_relative_gains)
            ),
            "incremental_value_directional_claim": directional_claim(
                incremental_revenue_interval,
                positive_label="INCREMENTAL_VALUE_AHEAD",
                negative_label="RULES_AHEAD",
            ),
            "incremental_value_seed_win_rate": round(
                sum(value > 0 for value in incremental_revenue_differences)
                / seeds,
                3,
            ),
        },
        "claim_guardrail": (
            "Synthetic paired evaluation only; do not present as merchant uplift."
        ),
        "runs": runs,
    }
