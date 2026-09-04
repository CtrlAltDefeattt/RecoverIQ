# RecoverIQ — Build Plan to September 5

## August 26 — Foundation

- Freeze V1 scope
- Implement correlated RecoveryGym environment
- Implement Random, Rules and LinUCB policies
- Implement safety engine
- Add deterministic benchmark and initial tests
- Publish an honest implemented-versus-planned README

**Exit criterion:** benchmark runs successfully and safety/signature tests pass.

## August 27 — Razorpay integration spike

**Code status:** webhook validation, normalization, mode gating, ordering tests,
Payment Link adapter, notification adapter, smoke script and deployment
blueprint are complete. Public staging receipt and a genuine Test Mode API call
remain pending until account secrets are configured outside GitHub.

- Deploy a minimal public staging webhook
- Configure Test Mode keys and webhook secret
- Verify signatures from the raw request body
- Receive one genuine Test Mode event
- Create one Standard Payment Link through the adapter
- Record integration limitations immediately

**Exit criterion:** external credentials, webhook delivery and one Test API call are de-risked early.

## August 28 — Evaluation-grade simulator

**Code status:** paired potential outcomes, evaluator-only counterfactual access,
natural-recovery and incremental-value decomposition, realized oracle regret,
segment/action diagnostics, synthetic-data checks and paired 95% confidence
intervals are complete. The committed report correctly identifies the rules
baseline as ahead of the current cold-start LinUCB learner.

- Add evaluator-only potential outcomes
- Compute oracle best action and cumulative regret
- Add paired multi-seed confidence reporting
- Add segment/action analysis and synthetic-data checks

**Exit criterion:** no cherry-picked single seed is needed to explain performance.

## August 29 — Incremental-value layer

**Code status:** a six-model observable logistic T-learner, balanced logged-
history warm start, executed-action-only online updates, per-action probability/
uplift/net-value estimates, calibration metrics and a decision explanation API
are complete. Across 10 paired seeds, it beats rules by a mean 9.61% simulated
recovered revenue with a 95% interval of 7.47% to 11.75% and a 10/10 seed win
rate. These figures are explicitly synthetic.

- Estimate no-action recovery from observable features
- Estimate candidate-action outcomes
- Calculate estimated uplift and expected net value
- Keep hidden simulator probabilities unavailable to the policy

**Exit criterion:** decision detail can show estimated natural recovery, action recovery and incremental value without reading simulator truth.

## August 30 — Bounded journey and budget

**Code status:** the two-intervention state machine, explicit wait/stop/
exhaustion/escalation outcomes, 24-hour cooldown, no-repeat action rule, batch
budget allocator, API endpoints and deterministic 500-journey scenario are
complete. All scenario invariants are machine-checked.

- Add a two-intervention case state machine
- Add `STOP`, exhausted and escalation terminal states
- Add cooldown/contact budgets
- Add batch intervention allocation

**Exit criterion:** a multi-step journey stops deterministically and batch limits are respected.

## August 31 — Persistence and Safety Gauntlet

**Code status:** SQLite event/case/decision/action/outcome/audit tables,
database-enforced event and action idempotency, terminal out-of-order capture
handling, pre-call execution reservation and a seven-scenario persisted Safety
Gauntlet are complete. The repository now passes 64 Python tests, with one
additional Neon integration test enabled when a test database URL is available.

- Replace in-memory event IDs with SQLite unique constraints
- Persist cases, events, decisions, actions and outcomes
- Handle out-of-order terminal events
- Add duplicate, opt-out, amount-limit, retry-limit and already-paid tests

**Exit criterion:** unsafe or duplicate execution is deterministically prevented and auditable.

## September 1 — Dashboard

**Code status:** the deployed responsive Command Center, Decision Detail,
Learning Lab and Safety & Audit screens are complete. Every displayed metric is
loaded from the dashboard backend route, with explicit synthetic labels,
loading/error states, accessible navigation and five frontend contract tests.

- Command Center
- Decision Detail
- Learning and baseline comparison
- Safety Gauntlet and audit trail

**Exit criterion:** every displayed number comes from the backend.

## September 2 — Final experiments

**Code status:** the benchmark is frozen at 30 paired seeds and 10,000 cases
per seed, with a canonical configuration digest, deterministic parallel
execution, complete per-seed evidence, variability and negative-seed analysis,
and three committed SVG charts. The incremental-value policy wins 30/30 seeds
against fixed rules with a mean 11.697% simulated recovered-revenue gain and a
95% interval of 11.350% to 12.043%. These figures are explicitly synthetic.

- Run 30 or more paired seeds if runtime permits
- Generate final metrics and charts
- Report variability, negative seeds and limitations
- Freeze benchmark configuration

**Exit criterion:** complete. Every final headline number traces to the frozen
configuration and committed report.

## September 3 — Deployment and repository polish

**Code status:** the dashboard and FastAPI backend are deployed as separate,
public Vercel production projects. Native Next.js and FastAPI entrypoints, a
deterministic shadow-mode demo seed, CI secret/local-state scanning, a complete
setup and deployment guide, and an accessible architecture SVG are committed.
The source repository remains private while reviewer-facing aliases are public.

- Deploy backend and frontend
- Add architecture graphic and setup instructions
- Add seeded demo-data workflow
- Verify repository hygiene and secrets

## September 4 — Five-minute pitch

**Code status:** the live database probe, signed production webhook smoke test,
timestamped pitch script, demo runbook and submission checklist are complete. A
genuine Razorpay Test Mode `payment.failed` delivery has been processed through
Vercel and persisted in Neon with the full decision/audit trace. A Payment Link
API call through the committed adapter remains optional final evidence.

- Record one real Test Mode recovery
- Show one blocked or approval-required action
- Show the learning curve and batch comparison
- Rehearse technical questions and limitations

## September 5 — Buffer and submission

- Bug fixes only
- Verify public repository, demo and video links
- Submit

## Explicit cuts

- No chatbot
- No voice or WhatsApp integration
- No deep RL
- No production money movement
- No unrelated revenue-recovery use cases
