# RecoverIQ

### Safety-constrained adaptive revenue recovery for Razorpay

[![RecoverIQ CI](https://github.com/CtrlAltDefeattt/RecoverIQ/actions/workflows/ci.yml/badge.svg)](https://github.com/CtrlAltDefeattt/RecoverIQ/actions/workflows/ci.yml)
![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Next.js 16](https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs&logoColor=white)
![Deployment](https://img.shields.io/badge/Deployment-Vercel-000000?logo=vercel&logoColor=white)
![Mode](https://img.shields.io/badge/Execution-Shadow%20Mode-F59E0B)

> RecoverIQ estimates which permitted intervention is most valuable for the
> current failed-payment context, executes through a bounded safety layer, and
> learns only from actions whose outcomes were actually observed.

**Razorpay AI Buildathon · Track 03 — AI Revenue Recovery**

[Live Command Center](https://recoveriq-dashboard-prajwal-ai.vercel.app) ·
[API Health](https://recoveriq-api.vercel.app/health) ·
[Architecture](docs/ARCHITECTURE.md) ·
[Verified Razorpay Test Mode evidence](docs/RAZORPAY_TEST_MODE_EVIDENCE.md)

---

## The problem

A failed payment is not one uniform recovery problem. Some customers recover
naturally, some benefit from a reminder or a new payment path, and some should
not be contacted because of consent, attempt, amount, or terminal-state rules.

Static workflows can optimize the probability of payment while missing the
more useful question: **did the intervention create incremental value compared
with doing nothing?** RecoverIQ provides the decision and control layer above
existing recovery primitives such as Payment Links and reminders.

## What makes RecoverIQ different

| Concern | RecoverIQ approach |
|---|---|
| Action selection | Estimates natural recovery and per-action response from observable context |
| Objective | Maximizes expected incremental net value, not contact volume |
| Journey control | Supports `WAIT`, `STOP`, approval escalation, cooldowns, and a two-action ceiling |
| Portfolio control | Allocates a shared budget across positive-value, safety-permitted cases |
| Learning boundary | Updates only the executed action model from its observed outcome |
| Safety | Masks unsafe actions before selection and applies a final deterministic veto |
| Reliability | Uses database-enforced event and action idempotency with terminal capture ordering |
| Explainability | Persists the context, estimates, reason codes, decision, action, and audit sequence |

Money-path decisions are intentionally measurable and bounded. The core does
not depend on an LLM to approve or execute financial actions.

## System architecture

![RecoverIQ deployment and decision architecture](docs/assets/recoveriq-architecture.svg)

The model proposes; the safety engine disposes. A blocked or approval-pending
proposal is not treated as a failed customer outcome and cannot update the
learner.

Read the complete [architecture and boundary design](docs/ARCHITECTURE.md).

## Evidence at a glance

| Evidence | Verified result |
|---|---|
| Frozen evaluation | 30 paired seeds × 10,000 synthetic cases per seed |
| Incremental-value policy vs fixed rules | +11.697% mean simulated recovered revenue |
| Paired 95% interval | +11.350% to +12.043% |
| Seed wins | 30 / 30 |
| Selected-action probability MAE | 5.166 percentage points |
| Persisted Safety Gauntlet | 7 / 7 scenarios passed |
| Incoming Razorpay path | Genuine Test Mode `payment.failed` event processed through Vercel and Neon |
| Outgoing Razorpay path | Genuine ₹1 Test Mode Payment Link created by the committed adapter |

The benchmark is synthetic engineering evidence, not measured merchant uplift
or a causal production claim. The repository retains negative baseline results
and publishes its confidence intervals, evaluator boundary, and limitations.

- [Evaluation methodology and final results](docs/EVALUATION.md)
- [Razorpay Test Mode integration receipt](docs/RAZORPAY_TEST_MODE_EVIDENCE.md)
- [Persistence and Safety Gauntlet](docs/PERSISTENCE_AND_SAFETY.md)

## Recovery actions

```text
NO_ACTION · REMINDER · RETRY_24H · PAYMENT_LINK · ALT_PAYMENT · PARTIAL_PAYMENT
```

`RETRY_24H` is a simulator action. A live implementation must restrict it to an
eligible subscription or mandate workflow; RecoverIQ does not present it as a
generic retry API for arbitrary payments.

## Repository structure

```text
RecoverIQ/
├── backend/app/
│   ├── adapters/       # Razorpay execution boundary
│   ├── api/            # Simulation and signed webhook routes
│   ├── domain/         # Events, recovery actions, and economics
│   ├── journeys/       # Bounded orchestration and batch allocation
│   ├── policies/       # Rules, LinUCB, and incremental-value policy
│   ├── safety/         # Deterministic policy engine
│   ├── services/       # Integration workflow
│   ├── simulator/      # RecoveryGym and evaluation tooling
│   └── storage/        # SQLite/Postgres repository implementations
├── experiments/        # Reproducible benchmark entrypoints and frozen config
├── frontend/           # Next.js reviewer command center
├── scripts/            # Hygiene, seeding, and Test Mode smoke utilities
├── tests/              # Unit, integration, ordering, and safety tests
├── outputs/            # Committed reproducibility artifacts and charts
└── docs/               # Architecture, evaluation, operations, and evidence
```

## Quick start

### Requirements

- Python 3.12+
- Node.js 22.13+
- npm 10+

### Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
python -m pytest -q
uvicorn backend.app.main:app --reload
```

On Windows, activate the environment with `.venv\\Scripts\\activate` and copy
`.env.example` to `.env` manually.

### Dashboard

```bash
cd frontend
npm ci
npm run check
npm run dev
```

The dashboard is available at `http://localhost:3000`; the API defaults to
`http://localhost:8000`.

## Safe configuration

The committed defaults are intentionally fail-closed:

```dotenv
RECOVERIQ_MODE=shadow
RECOVERIQ_EXECUTE_RAZORPAY_ACTIONS=false
```

Copy `.env.example` locally and supply credentials only through local or Vercel
environment variables. Never commit Razorpay keys, the webhook secret, or a
Neon connection string.

Production uses the pooled `DATABASE_URL` for Neon Postgres. Local development
and CI use SQLite through the same repository contract. On Vercel, the signed
webhook route returns `503` when durable storage is unavailable rather than
acknowledging work that could disappear with the function instance.

See [deployment and configuration](docs/DEPLOYMENT.md) for the complete runbook.

## API surface

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Process health |
| `GET` | `/health/database` | Durable ledger connectivity without secret disclosure |
| `GET` | `/readiness` | Safe configuration booleans and execution posture |
| `GET` | `/api/simulations/decision` | Explain one context-aware recommendation |
| `GET` | `/api/simulations/journey` | Simulate one bounded recovery journey |
| `POST` | `/api/simulations/run` | Run a deterministic policy benchmark |
| `POST` | `/api/simulations/batch` | Allocate a constrained batch budget |
| `POST` | `/webhooks/razorpay` | Receive signed Razorpay payment events |

Interactive API documentation is available at
[`/docs`](https://recoveriq-api.vercel.app/docs).

## Reproduce the evidence

```bash
python -m experiments.run_benchmark --events 1000 --seed 42
python -m experiments.run_day5_scenarios \
  --journey-cases 500 --batch-cases 100 --seed 42 \
  --budget-paise 5000 --max-actions 25 \
  --output outputs/day5_journey_budget_demo.json
python -m experiments.run_day6_safety_gauntlet \
  --output outputs/day6_safety_gauntlet.json
python -m scripts.check_repo_hygiene
```

The frozen 30-seed benchmark is intentionally separate because it is more
expensive:

```bash
python -m experiments.run_day8_final
```

## Documentation

| Document | Purpose |
|---|---|
| [Documentation index](docs/README.md) | Reviewer and developer navigation |
| [Product specification](docs/PRODUCT_SPEC.md) | Scope, domain model, metrics, and constraints |
| [Architecture](docs/ARCHITECTURE.md) | Component and data-boundary design |
| [Decision model](docs/MODEL.md) | Observable incremental-value learner |
| [Journey orchestration](docs/ORCHESTRATION.md) | State machine and batch allocator |
| [Persistence and safety](docs/PERSISTENCE_AND_SAFETY.md) | Idempotency, ordering, and Safety Gauntlet |
| [Evaluation](docs/EVALUATION.md) | Frozen experiment contract and results |
| [Deployment](docs/DEPLOYMENT.md) | Vercel and Neon setup |
| [Demo runbook](docs/DEMO_RUNBOOK.md) | Safe reviewer walkthrough |

## Current operating boundary

- Razorpay execution is disabled by default and the public reviewer deployment
  remains in Shadow Mode.
- The dashboard is read-only and labels synthetic values explicitly.
- A full transactional outbox, authenticated operator access, encrypted
  sensitive fields, retention policies, and a randomized merchant holdout are
  required before any live-money rollout.

For responsible vulnerability reporting, see [SECURITY.md](SECURITY.md).
