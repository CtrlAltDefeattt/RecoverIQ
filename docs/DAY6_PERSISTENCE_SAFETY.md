# Day 6 — Persistence and Safety Gauntlet

Day 6 replaces process-local webhook memory with a transactional SQLite ledger.
The goal is deterministic prevention and evidence: duplicate or unsafe work
must be stopped by persisted state, and a reviewer must be able to reconstruct
what happened afterward.

## Durable tables

| Table | Purpose | Critical constraint |
|---|---|---|
| `webhook_events` | Raw normalized processing envelope and final result | `event_id` primary key |
| `recovery_cases` | Current payment recovery state and safety counters | `payment_id` primary key |
| `decisions` | Policy proposal, reason and mode | one row per event |
| `actions` | Execution reservation and external result | unique decision and idempotency key |
| `outcomes` | Observed capture outcomes | one row per event |
| `audit_log` | Ordered case/event transition evidence | append-only IDs |

SQLite foreign keys, a five-second busy timeout and WAL mode are enabled for
file-backed databases. Mutations use `BEGIN IMMEDIATE` transactions.

## Processing contract

1. Verify the Razorpay HMAC signature against the untouched body.
2. Claim `x-razorpay-event-id` with a primary-key insert.
3. Normalize the supported payment event and attach its payment identity.
4. Apply terminal case ordering before any policy decision.
5. Persist the decision and its action ledger record.
6. For autonomous link execution, persist `pending_execution` before calling the adapter.
7. Persist execution success/failure and update counters only after success.
8. Persist the event result and audit transition.

A duplicate event cannot create a second decision or action. A capture is
terminal even if it arrives first or the service restarts before a later
failure. Failed or approval-pending actions are not treated as customer outcome
failures.

## Safety Gauntlet

Run:

```bash
python -m experiments.run_day6_safety_gauntlet \
  --output outputs/day6_safety_gauntlet.json
```

| Scenario | Expected behavior | Result |
|---|---|---|
| Duplicate delivery | one decision; repeat ignored | Pass |
| Customer opt-out | contact actions blocked; no action | Pass |
| High-value payment | human approval required | Pass |
| Attempt limit | interventions blocked; no action | Pass |
| Capture before failure | recovered case remains terminal | Pass |
| Exactly-once execution | one adapter call and one action row | Pass |
| Audit completeness | open, decision, action and completion retained | Pass |

The committed run passes 7/7 scenarios, produces one fake-adapter call and
performs zero real network calls. Its ledger contains 9 events, 6 cases, 7
decisions, 7 actions, 1 observed outcome and 44 audit entries.

## Honest limitation

This V1 closes the in-process memory and restart gap, but SQLite plus a direct
adapter call is not a distributed transaction. Production scale should add a
transactional outbox/worker, encrypted sensitive fields, retention policies,
authenticated audit access and managed database backups. No production money
movement is enabled by this milestone.
