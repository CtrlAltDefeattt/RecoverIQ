# RecoverIQ — Safety-Constrained Adaptive Revenue Recovery

RecoverIQ is an adaptive decision system for Razorpay AI Buildathon Track 03 — AI Revenue Recovery.

## One-line thesis

**RecoverIQ estimates which permitted intervention is most valuable for the current failed-payment context, executes through a bounded safety layer, and learns only from actions whose outcomes were actually observed.**

It is intentionally not an LLM-first system. Money-path decisions are measurable, bounded and auditable.

> **Project status:** Day-1 foundation. The repository currently contains a reproducible synthetic environment, three policies, safety rules, benchmark scripts, webhook signature verification and a Razorpay Payment Link adapter. Sequential journeys, explicit intervention-uplift estimation, durable persistence, budget allocation and the dashboard are scheduled milestones—not completed features.

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
- Money-denominated reward
- `ALLOW`, `REQUIRE_APPROVAL` and `BLOCK` safety decisions
- Autonomous action masking before policy selection, plus final safety veto
- No model update for blocked or approval-pending actions
- Razorpay webhook HMAC-SHA256 verification
- Duplicate-event protection for the current single-process API
- Standard Payment Link adapter
- Deterministic single-seed and multi-seed benchmarks
- Safety and signature tests

## Planned before September 5

- Evaluator-only potential outcomes and oracle regret
- Explicit estimated natural-recovery and intervention-uplift values
- Two-step bounded recovery journey with `STOP`
- Batch intervention budgets
- Durable SQLite event, action and audit stores
- Out-of-order webhook handling and idempotent execution
- Shadow, Assisted and Autonomous operating modes
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
  --output outputs/preliminary_10k_multiseed.json
```

Run the API:

```bash
uvicorn backend.app.main:app --reload
```

Endpoints:

```text
GET  /health
POST /api/simulations/run?events=1000&seed=42
POST /webhooks/razorpay
```

## Razorpay integration notes

- Webhook signatures use the unmodified raw request body.
- Duplicate events are identified with `x-razorpay-event-id`.
- The current in-memory duplicate set is development-only and will be replaced with a durable unique constraint.
- The large-scale benchmark uses `RecoveryGym`; it does not create thousands of Test Mode Payment Links.

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
