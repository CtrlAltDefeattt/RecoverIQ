from fastapi.testclient import TestClient

from backend.app.domain.models import RecoveryAction
from backend.app.journeys.allocator import BatchBudgetAllocator
from backend.app.journeys.models import (
    InterventionRecord,
    JourneyCommand,
    JourneyState,
    JourneyStatus,
)
from backend.app.journeys.orchestrator import JourneyOrchestrator
from backend.app.journeys.simulator import simulate_journey
from backend.app.main import app
from backend.app.policies.incremental_value import IncrementalValuePolicy
from backend.app.simulator.environment import RecoveryGym
from backend.app.simulator.training import train_incremental_value_policy
from experiments.run_day5_scenarios import run_scenarios


def test_no_positive_incremental_value_emits_explicit_stop():
    environment = RecoveryGym(seed=42)
    context = environment.sample_context(0)
    state = JourneyState("journey_stop", context)
    orchestrator = JourneyOrchestrator(
        IncrementalValuePolicy(),
        environment.safety,
    )

    decision = orchestrator.next_decision(state, context.hours_since_failure)

    assert decision.command == JourneyCommand.STOP
    assert decision.reason == "NO_POSITIVE_INCREMENTAL_VALUE"
    assert state.status == JourneyStatus.STOPPED


def test_cooldown_returns_a_bounded_wait():
    environment = RecoveryGym(seed=42)
    context = environment.sample_context(1)
    state = JourneyState(
        "journey_wait",
        context,
        min_interval_hours=24,
        interventions=[
            InterventionRecord(
                sequence=1,
                action=RecoveryAction.REMINDER,
                executed_at_hours=10,
                recovered=False,
                recovered_amount_paise=0,
                reward_paise=-100,
                estimate={},
            )
        ],
    )
    orchestrator = JourneyOrchestrator(
        IncrementalValuePolicy(),
        environment.safety,
    )

    decision = orchestrator.next_decision(state, now_hours=20)

    assert decision.command == JourneyCommand.WAIT
    assert decision.retry_after_hours == 14
    assert state.status == JourneyStatus.WAITING

    boundary_decision = orchestrator.next_decision(state, now_hours=34)
    assert boundary_decision.command != JourneyCommand.WAIT


def test_failed_two_intervention_journey_becomes_exhausted():
    environment = RecoveryGym(seed=5)
    result = simulate_journey(
        environment.sample_context(2),
        train_incremental_value_policy(),
        environment,
    )

    assert result["status"] == "EXHAUSTED"
    assert result["intervention_count"] == 2
    assert sum(entry["command"] == "WAIT" for entry in result["timeline"]) == 1


def test_recovery_and_high_value_escalation_are_terminal():
    environment = RecoveryGym(seed=42)
    policy = train_incremental_value_policy()

    recovered = simulate_journey(
        environment.sample_context(0),
        policy,
        environment,
    )
    escalated = simulate_journey(
        environment.sample_context(23),
        train_incremental_value_policy(),
        environment,
    )

    assert recovered["status"] == "RECOVERED"
    assert recovered["intervention_count"] == 1
    assert escalated["status"] == "ESCALATED"
    assert escalated["stop_reason"] == "AMOUNT_ABOVE_AUTONOMOUS_LIMIT"


def test_batch_allocator_respects_budget_cap_and_case_uniqueness():
    environment = RecoveryGym(seed=12)
    contexts = [environment.sample_context(index) for index in range(40)]
    contexts.append(contexts[0])
    allocation = BatchBudgetAllocator(
        train_incremental_value_policy(history_events=600, epochs=2)
    ).allocate(contexts, budget_paise=1_000, max_actions=3)
    case_ids = [item["case_id"] for item in allocation["selected"]]

    assert allocation["spent_paise"] <= 1_000
    assert allocation["selected_count"] <= 3
    assert len(case_ids) == len(set(case_ids))
    assert allocation["skipped"]["duplicate_case"] == 1
    assert all(
        item["expected_incremental_value_paise"] > 0
        for item in allocation["selected"]
    )


def test_zero_batch_budget_executes_nothing():
    environment = RecoveryGym(seed=3)
    contexts = [environment.sample_context(index) for index in range(10)]
    allocation = BatchBudgetAllocator(
        train_incremental_value_policy(history_events=600, epochs=2)
    ).allocate(contexts, budget_paise=0, max_actions=10)

    assert allocation["spent_paise"] == 0
    assert allocation["selected_count"] == 0


def test_day5_scenario_report_enforces_every_invariant():
    report = run_scenarios(
        journey_cases=30,
        batch_cases=20,
        seed=5,
        budget_paise=2_000,
        max_actions=5,
    )

    assert all(report["invariant_checks"].values())
    assert report["journey_summary"]["maximum_interventions_observed"] <= 2


def test_journey_and_batch_api_endpoints():
    with TestClient(app) as client:
        journey = client.get("/api/simulations/journey?seed=42&event_index=0")
        batch = client.post(
            "/api/simulations/batch?events=20&budget_paise=1000&max_actions=3"
        )

    assert journey.status_code == 200
    assert journey.json()["status"] in {
        "RECOVERED",
        "STOPPED",
        "EXHAUSTED",
        "ESCALATED",
    }
    assert batch.status_code == 200
    assert batch.json()["spent_paise"] <= 1_000
    assert batch.json()["selected_count"] <= 3
