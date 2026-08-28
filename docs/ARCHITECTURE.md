# Architecture

```text
Razorpay Test Mode / RecoveryGym
             |
             v
      Event Ingestion
             |
 Signature / Durable Event Claim
        (SQLite UNIQUE)
             |
      Event Normalizer
 (failed / captured / ignored)
             |
             v
       Context Builder
             |
             v
   Adaptive Recovery Policy
 (Rules / LinUCB / Incremental Value)
             |
         proposal
             v
    Journey Orchestrator
 (wait / stop / two-action limit)
             |
             v
        Policy Engine
      /      |       \
   ALLOW   APPROVE   BLOCK
      |       |
      +---+---+
          v
       Mode Gate
 Shadow / Assisted / Autonomous
          |
    Execution Adapter
      /         \
Simulator      Razorpay
   |              |
   +------v-------+
          Outcome
             |
             v
       Reward Engine
        /          \
 observed only   selected action
      |               |
 Policy update   Evaluator-only truth
                       |
          natural / potential outcomes
          uplift / oracle regret / CI
                       |
                       v
                 Audit / Metrics
                       |
                       v
              SQLite Durable Ledger
       events / cases / decisions / actions /
                  outcomes / audit
```

## Boundary rule

The Razorpay adapter knows how to execute actions.
The simulator knows how to generate outcomes.
The policy knows how to select actions.
The safety engine can veto actions.
These components remain separable so benchmark logic cannot accidentally depend on Razorpay network calls.

## Day-3 evaluation boundary

Every policy receives the same generated contexts and hidden recovery ranks.
The selected action is executed before the `CounterfactualEvaluator` is called.
Only the observed selected-action reward is passed to `policy.update()`;
potential outcomes for unselected actions remain evaluator-only.

The oracle is restricted to actions the safety engine permits autonomously. Its
regret metric compares realized net value, after intervention and contact-fatigue
costs, rather than comparing recovery probability alone. Multi-seed comparisons
use paired per-seed differences and Student-t 95% confidence intervals.

## Day-4 learning boundary

The incremental-value policy imports no simulator or evaluator component. It
uses 26 observable context features and maintains one online logistic response
model per action. The `NO_ACTION` model estimates natural recovery; candidate
models estimate recovery after each intervention. Selection maximizes:

```text
estimated P(recovery | context, action) × amount - action cost
```

Historical warm-start generation stores one safety-permitted action and one
observed outcome per case. During live simulation, only the executed action's
model is updated. Unchosen potential outcomes remain available solely to the
post-decision evaluator for calibration and regret reporting.

## Day-5 journey and budget boundary

The journey orchestrator owns temporal case state. Before execution it checks
terminal status, the two-intervention ceiling, the 24-hour cooldown, previously
used actions and the safety engine's permitted set. `STOP`, `WAIT` and
`ESCALATE` are orchestration commands rather than learnable recovery actions.
After execution, only the observed selected action updates the policy.

The batch allocator operates one level above individual journeys. It admits
only safety-permitted actions with positive estimated incremental value, ranks
them deterministically by value per synthetic action cost and then respects the
portfolio budget, action-count cap and one-action-per-case constraint. The
journey simulator and API use deep-copied demo policies so one request cannot
mutate another request's cached model.

## Day-2 terminal-state rule

`payment.captured` is terminal for the payment ID. If a late or out-of-order
`payment.failed` event arrives afterward, RecoverIQ records it as stale and does
not reopen or execute recovery. This matches Razorpay's documented possibility
of a failed event being followed by capture for the same transaction.

## Day-6 persistence boundary

SQLite is now the source of truth for webhook identity and case terminality.
The service claims an event using a primary-key insert before normalization or
decision work. A duplicate insert fails atomically and produces no second
decision or action. Supported events then update case state and ledgers through
`BEGIN IMMEDIATE` transactions.

An autonomous external action is inserted with a unique idempotency key and a
`pending_execution` status before the adapter call. Success or failure is then
persisted, and only successful execution increments attempt/contact counters.
This closes the in-process duplicate gap. A full transactional outbox with
asynchronous delivery remains a production-hardening step beyond this V1.

Capture is terminal in the database, including when it arrives before a failure
or across process restarts. Later failure events are retained as ignored audit
records but cannot reopen the case.
