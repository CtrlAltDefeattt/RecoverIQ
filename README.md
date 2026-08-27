# RecoverIQ — Safety-Constrained Adaptive Revenue Recovery

RecoverIQ is an adaptive decision system for Razorpay AI Buildathon Track 03 — AI Revenue Recovery.

## One-line thesis

**RecoverIQ estimates which permitted intervention is most valuable for the current failed-payment context, executes through a bounded safety layer, and learns only from actions whose outcomes were actually observed.**

It is intentionally not an LLM-first system. Money-path decisions are measurable, bounded and auditable.

> **Project status:** Day-5 bounded recovery journey. RecoverIQ now carries each case through at most two interventions, enforces a 24-hour cooldown, terminates with an explicit recovery/stop/exhaustion/escalation state, and allocates a batch action budget by positive expected incremental value. The real Test Mode call and public webhook receipt remain pending until deployment secrets are configured; no credentials belong in this repository.

## Why this project

Razorpay already supplies recovery primitives such as Payment Links, reminders, partial payments and subscription retry workflows. RecoverIQ does not rebuild them. It provides the decision layer above those primitives:

1. Should the system intervene?
2. Which permitted action has the best expected value?
3. Should it execute, request approval or stop?
4. What outcome should be used for learning?

## Implemented now

- Correlated synthetic `RecoveryGym` environment
- Random and static-rule baselines
- LinUCB contextual-bandit policy
- Observable-feature incremental-value policy with one response model per action
- Balanced 6,000-case logged-history warm start with no counterfactual training labels
- Online update of only the executed action's response model
- Per-action natural recovery, intervention recovery, uplift and net-value estimates
- Reviewer-facing decision explanation endpoint
- Money-denominated reward
- `ALLOW`, `REQUIRE_APPROVAL` and `BLOCK` safety decisions
- Autonomous action masking before policy selection, plus final safety veto
- No model update for blocked or approval-pending actions
- Razorpay webhook HMAC-SHA256 verification
- `payment.failed` and `payment.captured` normalization
- Duplicate-event protection for the current single-process API
- Protection against a late failure reopening an already captured payment
- Shadow, Assisted and Autonomous execution gates
- Standard and partial Payment Link adapter
- Payment Link SMS/email notification adapter
- Fail-closed execution switch and credential readiness endpoint
- Render deployment blueprint and Test Mode smoke script
- Deterministic single-seed and multi-seed benchmarks
- Evaluator-only potential outcomes unavailable to policy selection or learning
- Paired cases and latent outcomes across every policy
- Explicit natural recovery, probability uplift and incremental net value
- Realized net-value oracle regret over autonomously permitted actions
- Segment/action diagnostics and synthetic-data validation
- Paired 95% confidence intervals with automatic claim guardrails
- Two-intervention journey orchestration with explicit `WAIT` and `STOP` commands
- Recovered, stopped, exhausted and approval-escalated terminal states
- 24-hour inter-intervention cooldown and no repeated action within a journey
- Batch allocator with budget, action-count and one-action-per-case constraints
- Journey and batch simulation API endpoints
- Safety, adapter, signature, webhook and ordering tests

## Planned before September 5

- Durable SQLite event, action and audit stores
- Durable out-of-order event handling and idempotent execution
- Four-screen React dashboard
- End-to-end Razorpay Test Mode recovery demo

## Recovery actions

1. `NO_ACTION`
2. `REMINDER`
3. `RETRY_24H`
4. `PAYMENT_LINK`
5. `ALT_PAYMENT`
6. `PARTIAL_PAYMENT`

`RETRY_24H` is currently a simulator action. A live implementation must restrict it to an eligible subscription or mandate workflow; it is not presented as a generic API-driven retry for arbitrary payments.

## Current benchmark language

The benchmark compares policies inside a synthetic environment. Its comparison metric is named:

```text
additional simulated revenue versus fixed rules
```

This is deliberately not described as real merchant uplift or a proven causal effect. Final submission numbers will use paired multi-seed runs and will be reported with variability and limitations.

Day 3 established that cold-start LinUCB trails rules. The committed Day-4 run
uses 10 paired seeds with 1,000 evaluation cases per seed. The new incremental-
value policy beats rules by a mean ₹122,335 in simulated recovered revenue, or
9.61%; the paired 95% interval for relative gain is 7.47% to 11.75%, and it wins
all 10 seeds. Its mean selected-action probability MAE against evaluator truth
is 5.89%. The evaluator emits `INCREMENTAL_VALUE_AHEAD`. These remain synthetic
engineering results, not merchant-performance claims.

The committed Day-5 scenario runs 500 bounded journeys and a 100-case batch.
Every journey reaches a terminal state, no journey exceeds two interventions,
and all 163 required cooldowns are observed. With a synthetic ₹50 intervention
budget and a 25-action cap, the allocator spends exactly ₹50 on 21 unique,
positive-value cases and reports ₹17,634.44 of estimated incremental value.
That value is a model estimate inside RecoveryGym, not realized merchant uplift.

## Architecture

```text
Razorpay Test Mode / RecoveryGym
             |
      Event validation
             |
       Context builder
             |
      Adaptive policy
             |
    Journey orchestrator
    (wait / stop / limit)
             |
        Safety engine
       /      |      \
    ALLOW  APPROVE  BLOCK
       |
   Execution adapter
       |
     Outcome
       |
 Reward + audit + learning
```

The model proposes; the safety engine disposes. A proposal that was blocked or is awaiting approval is not treated as a failed customer outcome.

## Run locally

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

macOS/Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Run the tests and benchmark:

```bash
pytest -q
python -m experiments.run_benchmark --events 1000 --seed 42
python -m experiments.run_multiseed --events 10000 --seeds 10 \
  --output outputs/multiseed_results.json
python -m experiments.run_day5_scenarios --journey-cases 500 \
  --batch-cases 100 --seed 42 --budget-paise 5000 --max-actions 25 \
  --output outputs/day5_journey_budget_demo.json
```

Run the API:

```bash
uvicorn backend.app.main:app --reload
```

Endpoints:

```text
GET  /health
GET  /readiness
GET  /api/simulations/decision?seed=42&event_index=0
GET  /api/simulations/journey?seed=42&event_index=0
POST /api/simulations/run?events=1000&seed=42
POST /api/simulations/batch?events=100&seed=42&budget_paise=5000&max_actions=25
POST /webhooks/razorpay
```

Test Mode Payment Link smoke test, after configuring Test credentials locally:

```bash
python -m scripts.razorpay_test_mode_smoke --amount-paise 100
```

## Razorpay integration notes

- Webhook signatures use the unmodified raw request body.
- Duplicate events are identified with `x-razorpay-event-id`.
- A captured payment is terminal, so a later failure for the same payment is ignored.
- Live execution requires both `RECOVERIQ_MODE=autonomous` and `RECOVERIQ_EXECUTE_RAZORPAY_ACTIONS=true`.
- The current in-memory duplicate set is development-only and will be replaced with a durable unique constraint.
- The large-scale benchmark uses `RecoveryGym`; it does not create thousands of Test Mode Payment Links.
- See `docs/DAY2_INTEGRATION.md` for deployment and webhook configuration.
- See `docs/DAY3_EVALUATION.md` for the evaluation contract and metric definitions.
- See `docs/DAY4_INCREMENTAL_VALUE.md` for the learner, leakage boundary and results.
- See `docs/DAY5_JOURNEY_BUDGET.md` for the state machine, allocation rules and scenario results.

References:

- https://razorpay.com/buildathon/
- https://razorpay.com/docs/webhooks/validate-test/
- https://razorpay.com/docs/api/payments/payment-links/create-standard/
- https://razorpay.com/docs/api/payments/payment-links/resend/
- https://razorpay.com/docs/payments/subscriptions/payment-retries/

## Submission claim rule

No number enters the pitch unless it is generated by a committed benchmark configuration. Synthetic findings will always be labelled synthetic, and unsupported claims about real merchant recovery performance are explicitly excluded.

## Non-goals before September 5

- Chatbot or voice agent
- LLM decision-making in the money path
- Deep reinforcement learning
- Production charging
- Complex authentication or multi-tenant administration
- Unsupported causal claims from observational merchant data
