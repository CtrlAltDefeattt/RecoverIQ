from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from backend.app.journeys.allocator import BatchBudgetAllocator
from backend.app.journeys.simulator import simulate_journey
from backend.app.simulator.environment import RecoveryGym
from backend.app.simulator.training import train_incremental_value_policy


def run_scenarios(
    journey_cases: int = 500,
    batch_cases: int = 100,
    seed: int = 42,
    budget_paise: int = 5_000,
    max_actions: int = 25,
) -> dict:
    if journey_cases <= 0 or batch_cases <= 0:
        raise ValueError("journey_cases and batch_cases must be positive")

    journey_environment = RecoveryGym(seed=seed)
    journey_policy = train_incremental_value_policy()
    journeys = [
        simulate_journey(
            journey_environment.sample_context(index),
            journey_policy,
            journey_environment,
        )
        for index in range(journey_cases)
    ]
    status_counts = Counter(journey["status"] for journey in journeys)
    representatives = {}
    for journey in journeys:
        representatives.setdefault(journey["status"], journey)

    batch_environment = RecoveryGym(seed=seed + 1)
    batch_contexts = [
        batch_environment.sample_context(index) for index in range(batch_cases)
    ]
    allocation = BatchBudgetAllocator(
        train_incremental_value_policy()
    ).allocate(
        batch_contexts,
        budget_paise=budget_paise,
        max_actions=max_actions,
    )
    selected_case_ids = [item["case_id"] for item in allocation["selected"]]
    terminal_statuses = {"RECOVERED", "STOPPED", "EXHAUSTED", "ESCALATED"}

    return {
        "configuration": {
            "journey_cases": journey_cases,
            "batch_cases": batch_cases,
            "seed": seed,
            "max_interventions_per_journey": 2,
            "minimum_intervention_interval_hours": 24,
            "batch_budget_paise": budget_paise,
            "batch_max_actions": max_actions,
        },
        "journey_summary": {
            "terminal_status_counts": dict(sorted(status_counts.items())),
            "all_journeys_terminal": all(
                journey["status"] in terminal_statuses for journey in journeys
            ),
            "maximum_interventions_observed": max(
                journey["intervention_count"] for journey in journeys
            ),
            "cooldown_wait_count": sum(
                entry["command"] == "WAIT"
                for journey in journeys
                for entry in journey["timeline"]
            ),
            "explicit_stop_count": sum(
                entry["command"] == "STOP"
                for journey in journeys
                for entry in journey["timeline"]
            ),
            "recovered_amount_paise": sum(
                intervention["recovered_amount_paise"]
                for journey in journeys
                for intervention in journey["interventions"]
            ),
        },
        "batch_allocation": allocation,
        "invariant_checks": {
            "all_journeys_terminal": all(
                journey["status"] in terminal_statuses for journey in journeys
            ),
            "journey_limit_respected": all(
                journey["intervention_count"] <= 2 for journey in journeys
            ),
            "budget_respected": allocation["spent_paise"] <= budget_paise,
            "action_cap_respected": allocation["selected_count"] <= max_actions,
            "one_action_per_case": len(selected_case_ids)
            == len(set(selected_case_ids)),
            "only_positive_allocations": all(
                item["expected_incremental_value_paise"] > 0
                for item in allocation["selected"]
            ),
        },
        "representative_journeys": representatives,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--journey-cases", type=int, default=500)
    parser.add_argument("--batch-cases", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--budget-paise", type=int, default=5_000)
    parser.add_argument("--max-actions", type=int, default=25)
    parser.add_argument("--output", default="outputs/day5_journey_budget_demo.json")
    args = parser.parse_args()

    report = run_scenarios(
        journey_cases=args.journey_cases,
        batch_cases=args.batch_cases,
        seed=args.seed,
        budget_paise=args.budget_paise,
        max_actions=args.max_actions,
    )
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "configuration": report["configuration"],
                "journey_summary": report["journey_summary"],
                "batch_summary": {
                    key: value
                    for key, value in report["batch_allocation"].items()
                    if key not in {"selected"}
                },
                "invariant_checks": report["invariant_checks"],
            },
            indent=2,
        )
    )
    print(f"Saved full results to {destination}")


if __name__ == "__main__":
    main()
