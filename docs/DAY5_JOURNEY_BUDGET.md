# Day 5 — Bounded Journeys and Batch Budgets

Day 5 turns the single-decision learner into a bounded recovery system. A case
can wait, execute a safe intervention, recover, stop, exhaust its intervention
limit or escalate for approval. A separate portfolio allocator decides which
positive-value cases fit inside a batch budget.

## Journey state machine

`STOP`, `WAIT` and `ESCALATE` are orchestration commands. They are deliberately
not added to `RecoveryAction`, so the learner cannot treat operational state as
a customer intervention.

| Current condition | Decision or terminal state |
|---|---|
| Already terminal | `STOP` with the existing status |
| Two interventions executed without recovery | `EXHAUSTED` |
| Fewer than 24 hours since the previous intervention | `WAIT` with retry time |
| Best positive action requires approval | `ESCALATE` |
| No safety-permitted action has positive incremental value | `STOPPED` |
| Safe positive action exists | `EXECUTE` |
| Executed action recovers payment | `RECOVERED` |

Additional invariants:

- At most two interventions execute per case.
- The same action cannot execute twice in one journey.
- Existing attempt, contact, opt-out, recovery and amount safety gates still apply.
- Policy updates use the exact pre-action context and only the observed selected outcome.

## Batch allocation

For each unique case, the allocator selects its highest-value autonomously
permitted action. Candidates with non-positive estimated incremental value are
discarded. Remaining candidates are ranked by estimated incremental value per
synthetic action-cost unit, with deterministic tie-breaking, then selected
until the budget or action cap is reached.

The report includes selected cases, spend, remaining budget, expected
incremental value, segment distribution and skip reasons. This is a transparent
greedy heuristic, not a claim of globally optimal allocation.

## Committed scenario

Run:

```bash
python -m experiments.run_day5_scenarios --journey-cases 500 \
  --batch-cases 100 --seed 42 --budget-paise 5000 --max-actions 25 \
  --output outputs/day5_journey_budget_demo.json
```

The seeded run produces:

| Check | Result |
|---|---:|
| Journeys terminal | 500 / 500 |
| Recovered | 263 |
| Explicitly stopped | 205 |
| Exhausted after two interventions | 22 |
| Escalated for approval | 10 |
| Required cooldown waits observed | 163 |
| Maximum interventions observed | 2 |
| Batch budget | ₹50.00 |
| Batch actions selected | 21 / 25 cap |
| Batch spend | ₹50.00 |
| Estimated incremental value | ₹17,634.44 |

All six scenario invariants pass: terminal journeys, intervention limit,
budget, action cap, unique case allocation and positive-value allocation.
Results are synthetic RecoveryGym engineering evidence. Estimated incremental
value is not realized revenue or a merchant-performance claim.

## API

```text
GET  /api/simulations/journey?seed=42&event_index=0
POST /api/simulations/batch?events=100&seed=42&budget_paise=5000&max_actions=25
```

The next persistence milestone must make journey transitions, approvals and
executions durable and idempotent before any real autonomous deployment.
