# Day 4 — Observable Incremental-Value Learning

## What changed

Day 3 proved that cold-start LinUCB underperformed the rules baseline. Day 4 adds
an explicit outcome-modeling policy that estimates natural recovery and every
permitted intervention from observable context, then selects the highest
expected net value.

## Model

RecoverIQ uses an online logistic T-learner with one model for each action:

```text
NO_ACTION model        -> estimated natural recovery
Intervention model     -> estimated recovery after that action
Estimated uplift       -> intervention probability - natural probability
Expected net value     -> intervention probability × amount - action cost
Incremental net value  -> action net value - natural expected value
```

The 26 inputs contain payment amount, customer-history summaries, attempts,
contact frequency, failure timing and categorical segment/failure/method fields.
They do not contain simulator probabilities, latent recovery ranks, potential
outcomes or oracle actions.

## Logged-history warm start

- 6,000 unique historical synthetic cases
- one safety-permitted action per case
- one observed outcome per case
- deterministic balanced exploration across the six actions
- four offline training replays
- fixed training seed, separate from evaluation seeds

The generator never requests unchosen outcomes. Online evaluation subsequently
updates only the model belonging to the action that was actually executed.

## Decision explanation

```text
GET /api/simulations/decision?seed=42&event_index=0
```

The response contains the observable context, safety-permitted actions, natural
recovery estimate, candidate recovery estimate, estimated uplift, action cost,
expected net value, expected incremental value and the selected action. It does
not expose evaluator truth.

## Paired Day-4 result

Configuration:

```text
1,000 evaluation cases per seed
10 paired seeds
6,000 separate logged-history cases
```

Result versus fixed rules:

```text
Mean additional simulated recovered revenue: ₹122,335
Mean relative gain: 9.61%
95% paired interval for relative gain: 7.47% to 11.75%
Seed win rate: 10/10
Directional guardrail: INCREMENTAL_VALUE_AHEAD
```

Calibration summary across the 10 runs:

```text
Mean selected-action probability MAE: 5.89 percentage points
Mean natural-recovery probability MAE: 7.84 percentage points
Mean selected-outcome Brier score: 0.2248
```

These are synthetic paired-evaluation results. They are not a measured causal
uplift claim for Razorpay merchants.

## Reproduce

```bash
python -m experiments.run_multiseed --events 1000 --seeds 10 \
  --output outputs/day4_incremental_value_1000x10.json
```
