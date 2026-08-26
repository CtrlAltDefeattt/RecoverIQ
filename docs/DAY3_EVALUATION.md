# Day 3 — Evaluation-Grade Simulator

## Why this milestone exists

A single random seed can make an adaptive policy look better or worse by luck.
RecoverIQ now compares policies on identical cases and deterministic hidden
customer responses, then reports uncertainty across paired seeds.

## Evaluation contract

1. Every policy receives the same `RecoveryContext` sequence for a given seed.
2. Every action shares the same hidden customer recovery rank for that case.
3. The policy selects an action without seeing probabilities or counterfactuals.
4. The environment reveals only the selected action's observed reward to learning.
5. After selection, an evaluator computes potential outcomes for scoring only.
6. The oracle may choose only actions permitted by the autonomous safety mask.

This produces monotonic potential outcomes: if one permitted action has a higher
success probability than another, it cannot fail when the lower-probability
action succeeds for the same synthetic customer.

## Reported metrics

| Metric | Meaning |
|---|---|
| Natural recovery | Outcome/probability under `NO_ACTION` |
| Probability uplift | Selected-action probability minus natural recovery probability |
| Expected incremental value | Difference in expected recovered amount, net of action cost |
| Realized incremental revenue | Selected recovered amount minus no-action recovered amount |
| Realized incremental net value | Incremental revenue minus intervention/contact-fatigue cost |
| Oracle regret | Best permitted realized net value minus selected realized net value |
| Paired 95% CI | Student-t interval over same-seed policy differences |

## Claim guardrail

The report emits one of `LINUCB_AHEAD`, `RULES_AHEAD` or `INCONCLUSIVE` based on
whether the 95% interval lies wholly above zero, wholly below zero, or crosses
zero. All outputs are labeled synthetic and must not be presented as measured
merchant uplift.

## Committed Day-3 run

Configuration:

```text
1,000 cases per seed
10 paired seeds
LinUCB alpha = 0.8
```

Result:

```text
Mean LinUCB minus rules recovered revenue: -₹143,640
95% paired interval: -₹188,191 to -₹99,090
LinUCB seed win rate: 0/10
Guardrail: RULES_AHEAD
```

This negative result is useful: it establishes a reproducible baseline for the
incremental-value learner milestone and prevents the pitch from overstating the
current adaptive policy.

## Reproduce

```bash
python -m experiments.run_multiseed --events 1000 --seeds 10 \
  --output outputs/day3_paired_1000x10.json
```
