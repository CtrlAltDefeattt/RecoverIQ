from __future__ import annotations
from statistics import mean

from backend.app.policies.baselines import RandomPolicy, RuleBasedPolicy
from backend.app.policies.linucb import LinUCBPolicy
from backend.app.simulator.environment import RecoveryGym


def run_policy(policy, events: int, seed: int) -> dict:
    env = RecoveryGym(seed=seed)
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

    for i in range(events):
        ctx = env.sample_context(i)
        at_risk_paise += ctx.amount_paise
        allowed_actions = env.safety.allowed_actions(ctx)
        action = policy.select_action(ctx, allowed_actions=allowed_actions)
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

        # A blocked or approval-pending proposal was never executed, so zero is
        # not a customer outcome. Learning from it would incorrectly teach the
        # policy that the action failed.
        if outcome.outcome_observed:
            policy.update(ctx, action, outcome.reward_paise)

    return {
        "events": events,
        "revenue_at_risk_rupees": round(at_risk_paise / 100, 2),
        "recovered_revenue_rupees": round(recovered_paise / 100, 2),
        "recovery_rate": round(successes / events, 4),
        "avg_reward_rupees": round(mean(rewards) / 100, 2),
        "blocked_actions": blocks,
        "approval_required": approvals,
        "executed_actions": executed_actions,
        "observed_outcomes": observed_outcomes,
        "no_actions": no_actions,
        "action_counts": action_counts,
    }


def benchmark(events: int = 1000, seed: int = 42) -> dict:
    results = {
        "random": run_policy(RandomPolicy(seed), events, seed),
        "rules": run_policy(RuleBasedPolicy(), events, seed),
        "linucb": run_policy(LinUCBPolicy(alpha=0.8), events, seed),
    }

    rules_recovered = results["rules"]["recovered_revenue_rupees"]
    linucb_recovered = results["linucb"]["recovered_revenue_rupees"]

    results["comparison"] = {
        "linucb_additional_simulated_rupees_vs_rules": round(
            linucb_recovered - rules_recovered, 2
        ),
        "linucb_relative_gain_pct_vs_rules": round(
            ((linucb_recovered - rules_recovered) / rules_recovered * 100)
            if rules_recovered
            else 0.0,
            2,
        ),
    }
    return results
