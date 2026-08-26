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

- Estimate no-action recovery from observable features
- Estimate candidate-action outcomes
- Calculate estimated uplift and expected net value
- Keep hidden simulator probabilities unavailable to the policy

**Exit criterion:** decision detail can show estimated natural recovery, action recovery and incremental value without reading simulator truth.

## August 30 — Bounded journey and budget

- Add a two-intervention case state machine
- Add `STOP`, exhausted and escalation terminal states
- Add cooldown/contact budgets
- Add batch intervention allocation

**Exit criterion:** a multi-step journey stops deterministically and batch limits are respected.

## August 31 — Persistence and Safety Gauntlet

- Replace in-memory event IDs with SQLite unique constraints
- Persist cases, events, decisions, actions and outcomes
- Handle out-of-order terminal events
- Add duplicate, opt-out, amount-limit, retry-limit and already-paid tests

**Exit criterion:** unsafe or duplicate execution is deterministically prevented and auditable.

## September 1 — Dashboard

- Command Center
- Decision Detail
- Learning and baseline comparison
- Safety Gauntlet and audit trail

**Exit criterion:** every displayed number comes from the backend.

## September 2 — Final experiments

- Run 30 or more paired seeds if runtime permits
- Generate final metrics and charts
- Report variability, negative seeds and limitations
- Freeze benchmark configuration

## September 3 — Deployment and repository polish

- Deploy backend and frontend
- Add architecture graphic and setup instructions
- Add seeded demo-data workflow
- Verify repository hygiene and secrets

## September 4 — Five-minute pitch

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
