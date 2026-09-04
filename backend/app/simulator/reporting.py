from __future__ import annotations

import hashlib
import json
import math
from statistics import mean, median, stdev

POLICIES = ("random", "rules", "linucb", "incremental_value")


def canonical_config_digest(config: dict) -> str:
    encoded = json.dumps(
        config,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_final_config(config: dict) -> None:
    required = {
        "benchmark_id",
        "events_per_seed",
        "seed_count",
        "seed_start",
        "workers",
        "linucb_alpha",
        "incremental_value_training",
        "confidence_level",
        "synthetic_only",
    }
    missing = sorted(required - set(config))
    if missing:
        raise ValueError(f"Missing frozen benchmark fields: {', '.join(missing)}")
    if config["events_per_seed"] <= 0:
        raise ValueError("events_per_seed must be positive")
    if config["seed_count"] < 30:
        raise ValueError("Day 8 final benchmark requires at least 30 seeds")
    if config["seed_start"] != 0:
        raise ValueError("The current paired benchmark requires seed_start=0")
    if config["workers"] <= 0:
        raise ValueError("workers must be positive")
    if not 0 < config["confidence_level"] < 1:
        raise ValueError("confidence_level must be between zero and one")
    if config["confidence_level"] != 0.95:
        raise ValueError("The implemented interval is fixed at 95%")
    if config["linucb_alpha"] != 0.8:
        raise ValueError("Frozen code currently uses LinUCB alpha=0.8")
    training = config["incremental_value_training"]
    if training != {
        "history_events": 6000,
        "history_seed": 20260829,
        "epochs": 4,
    }:
        raise ValueError("Frozen incremental-value training settings changed")
    if config["synthetic_only"] is not True:
        raise ValueError("Day 8 results must remain explicitly synthetic")


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def distribution_summary(values: list[float]) -> dict:
    if not values:
        raise ValueError("At least one value is required")
    return {
        "n": len(values),
        "mean": round(mean(values), 3),
        "median": round(median(values), 3),
        "sample_std": round(stdev(values), 3) if len(values) > 1 else None,
        "minimum": round(min(values), 3),
        "q1": round(_percentile(values, 0.25), 3),
        "q3": round(_percentile(values, 0.75), 3),
        "maximum": round(max(values), 3),
        "negative_count": sum(value < 0 for value in values),
        "zero_count": sum(value == 0 for value in values),
        "positive_count": sum(value > 0 for value in values),
    }


def _policy_aggregates(runs: list[dict]) -> dict:
    aggregates = {}
    for policy in POLICIES:
        policy_runs = [run[policy] for run in runs]
        aggregates[policy] = {
            "mean_recovery_rate": round(
                mean(run["recovery_rate"] for run in policy_runs), 5
            ),
            "mean_recovered_revenue_rupees": round(
                mean(run["recovered_revenue_rupees"] for run in policy_runs), 2
            ),
            "mean_net_value_rupees": round(
                mean(run["total_net_value_rupees"] for run in policy_runs), 2
            ),
            "mean_oracle_regret_rupees": round(
                mean(
                    run["oracle_evaluation"]["oracle_regret_rupees"]
                    for run in policy_runs
                ),
                2,
            ),
        }
    incremental_runs = [run["incremental_value"] for run in runs]
    aggregates["incremental_value"]["mean_selected_probability_mae"] = round(
        mean(
            run["estimated_decision_metrics"][
                "selected_probability_mae_against_evaluator"
            ]
            for run in incremental_runs
        ),
        5,
    )
    aggregates["incremental_value"]["mean_selected_brier_score"] = round(
        mean(
            run["estimated_decision_metrics"]["selected_outcome_brier_score"]
            for run in incremental_runs
        ),
        5,
    )
    return aggregates


def _seed_rows(runs: list[dict], prefix: str) -> list[dict]:
    net_value_key = (
        "linucb_additional_simulated_net_value_rupees_vs_rules"
        if prefix == "linucb"
        else "incremental_value_additional_net_value_rupees_vs_rules"
    )
    return [
        {
            "seed": run["seed"],
            "additional_recovered_revenue_rupees_vs_rules": run["comparison"][
                f"{prefix}_additional_simulated_rupees_vs_rules"
            ],
            "additional_net_value_rupees_vs_rules": run["comparison"][
                net_value_key
            ],
            "relative_recovered_revenue_gain_pct": run["comparison"][
                f"{prefix}_relative_gain_pct_vs_rules"
            ],
            "oracle_regret_reduction_rupees_vs_rules": run["comparison"][
                f"{prefix}_oracle_regret_reduction_rupees_vs_rules"
            ],
        }
        for run in runs
    ]


def build_final_report(summary: dict, config: dict) -> dict:
    validate_final_config(config)
    if summary["events_per_seed"] != config["events_per_seed"]:
        raise ValueError("Result events do not match the frozen configuration")
    if summary["seed_count"] != config["seed_count"]:
        raise ValueError("Result seed count does not match the frozen configuration")

    runs = summary["runs"]
    incremental_rows = _seed_rows(runs, "incremental_value")
    linucb_rows = _seed_rows(runs, "linucb")
    incremental_gains = [
        row["relative_recovered_revenue_gain_pct"] for row in incremental_rows
    ]
    linucb_gains = [
        row["relative_recovered_revenue_gain_pct"] for row in linucb_rows
    ]

    return {
        "benchmark_id": config["benchmark_id"],
        "config_sha256": canonical_config_digest(config),
        "claim_guardrail": summary["claim_guardrail"],
        "evaluation_contract": summary["evaluation_contract"],
        "frozen_config": config,
        "paired_policy_comparison": summary["paired_policy_comparison"],
        "policy_aggregates": _policy_aggregates(runs),
        "variability": {
            "incremental_value_relative_gain_pct_vs_rules": (
                distribution_summary(incremental_gains)
            ),
            "linucb_relative_gain_pct_vs_rules": distribution_summary(
                linucb_gains
            ),
        },
        "negative_seeds": {
            "incremental_value": [
                row
                for row in incremental_rows
                if row["additional_recovered_revenue_rupees_vs_rules"] < 0
            ],
            "linucb": [
                row
                for row in linucb_rows
                if row["additional_recovered_revenue_rupees_vs_rules"] < 0
            ],
        },
        "seed_comparisons": {
            "incremental_value": incremental_rows,
            "linucb": linucb_rows,
        },
        "limitations": [
            "All customers, failures, responses, and amounts are synthetic.",
            "Paired potential outcomes are available only to the evaluator, not the policies.",
            "The logged-history warm start is generated by RecoveryGym rather than merchant traffic.",
            "The simulator does not model every Razorpay product eligibility or operational failure mode.",
            "Confidence intervals quantify seed variability inside this simulator, not external validity.",
            "No result is evidence of measured causal uplift for a real merchant.",
        ],
        "runs": runs,
    }
