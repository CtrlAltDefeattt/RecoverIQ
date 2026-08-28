# RecoverIQ V1 Product Specification

## 1. Problem

Merchants lose revenue after failed or abandoned payment journeys. Existing recovery primitives can execute retries, links, reminders and alternative paths, but the decision problem remains:

1. **Should we intervene at all?**
2. **Which permitted intervention has the highest expected incremental value?**
3. **When should we stop?**
4. **How do we learn from the outcome without allowing unsafe autonomous actions?**

RecoverIQ treats revenue recovery as a **sequential, safety-constrained decision problem**. The Day-5 implementation combines an observable incremental-value learner with a bounded two-intervention journey state machine and a constrained batch allocator.

## 2. Product hypothesis

The V1 target is to estimate, for a revenue-at-risk event with context `x` and candidate action `a`:

`incremental_value(a, x) = [P(pay | a, x) - P(pay | no_action, x)] * amount - action_cost - penalties`

The best action is not necessarily the action with the highest raw payment probability. It is the **legal, safe action with the highest expected incremental value**.

Until the explicit no-action estimator and evaluator-only counterfactual layer are implemented, benchmark differences are reported as **additional simulated revenue versus fixed rules**, not as a proven causal effect.

## 3. User

Primary user: Razorpay merchant / finance-growth operations team.

Secondary user: human reviewer approving high-risk recovery actions.

## 4. V1 recovery state

A recovery case contains:
- case_id
- merchant_id
- customer_id
- amount_paise
- failure_reason
- payment_method
- customer_segment
- lifetime_value_paise
- tenure_days
- historical_success_rate
- prior_recovery_success_rate
- attempts
- contacts_last_7d
- hours_since_failure
- opted_out
- already_recovered
- current_status

## 5. Actions

| Action | Meaning | Autonomous? |
|---|---|---|
| NO_ACTION | Wait; natural recovery may occur | Yes |
| REMINDER | Send bounded recovery reminder | Yes if policy allows |
| RETRY_24H | Schedule/recommend retry after cooldown | Yes in simulator; gated in integration |
| PAYMENT_LINK | Generate a fresh Test Mode payment link | Yes under threshold |
| ALT_PAYMENT | Offer alternate payment path | Yes under threshold |
| PARTIAL_PAYMENT | Offer partial-payment link | Approval for high values |

`STOP` is produced by policy/terminal state rather than treated as a bandit action.

### Journey contract

- A case receives at most two executed interventions.
- Consecutive interventions are separated by at least 24 hours.
- An action is not repeated within the same journey.
- Recovery, explicit stop, exhaustion and escalation are terminal.
- A positive action that requires approval becomes an escalation; it is not silently executed or learned as a failure.
- The learner updates only after the selected action executes and its outcome is observed.

### Batch contract

The allocator considers each case's best safety-permitted action with positive
estimated incremental value, ranks candidates by value per synthetic action
cost, and applies both a batch budget and action-count cap. It allocates at most
one action per case. This deterministic heuristic is auditable; it is not
presented as a globally optimal knapsack solver.

## 6. Safety policy

### Rules
- Already recovered → BLOCK
- Customer opted out → BLOCK contact/payment-link actions
- Max recovery attempts = 3
- Max contacts in 7 days = 3
- Minimum retry cooldown = 12 hours
- Duplicate event/action → BLOCK/IGNORE
- Amount > ₹10,000 → REQUIRE_APPROVAL for money-related recovery action
- Invalid webhook signature → REJECT
- Terminal successful case → BLOCK further recovery
- Policy decision is always persisted with reason codes

### Durable enforcement

Day 6 persists webhook events, recovery cases, decisions, action reservations,
observed outcomes and append-only audit entries in SQLite. Event IDs and action
idempotency keys have database unique constraints. A `payment.captured` state is
terminal, so a later failure is recorded as stale without reopening the case.
External execution is reserved before the adapter call and its completion or
failure is written back to the ledger.

### Principle
**The model proposes. The policy engine disposes.**

The ML policy is never allowed to bypass policy.

## 7. Modes

### Shadow
Model recommendation is logged but baseline policy acts.

### Assisted
Model recommendation requires human approval where configured.

### Autonomous
Only low-risk policy-approved actions execute automatically.

V1 UI needs to expose current mode.

## 8. RecoveryGym synthetic environment

The simulator generates correlated customer profiles rather than independent random columns.

### Example hidden segments
**LOYAL_SAAS**
- higher LTV
- high natural recovery
- strong response to alternate payment
- moderate response to payment link

**NEW_ECOM**
- low tenure
- lower natural recovery
- strong response to immediate reminder
- moderate payment-link response

**PRICE_SENSITIVE**
- medium LTV
- good partial-payment response
- weaker retry response

**RETRY_PRONE**
- repeated temporary balance failures
- strong delayed-retry response

The environment owns the hidden outcome function. The policy receives features but **cannot inspect hidden response probabilities**.

## 9. Reward

Initial V1:

`reward = recovered_amount - intervention_cost - fatigue_penalty - unsafe_action_penalty`

Suggested costs in simulation:
- no action: ₹0
- reminder: ₹1
- retry: ₹2
- payment link: ₹3
- alternate payment: ₹3
- partial payment: ₹4

These are synthetic optimization costs, not claims about Razorpay pricing.

## 10. Baselines

### A. RandomPolicy
Chooses any available action.

### B. RuleBasedPolicy
Human-authored deterministic rules.

Example:
- insufficient funds + low attempts → retry
- authentication failure → alternate payment
- high amount + price-sensitive → partial payment
- otherwise → payment link

### C. LinUCBPolicy
Contextual bandit:
- one parameter vector per action
- observes context vector
- chooses action by upper confidence bound
- updates from observed monetary reward

Why LinUCB for V1:
- online learning
- interpretable
- fast
- no deep-RL instability
- implementable and explainable before deadline

Blocked and approval-pending proposals are never used as zero-reward learning examples. The policy updates only after an action was executed and its outcome observed.

### D. IncrementalValuePolicy
An observable logistic T-learner:
- one response model for `NO_ACTION` natural recovery
- one response model for each intervention
- action selection by estimated net value
- warm-started from one logged action/outcome per historical case
- updates only the model for the executed, observed action
- exposes probability, uplift and value estimates for decision explanation

Simulator probabilities and unselected potential outcomes are forbidden inputs.

## 11. Experiment design

### Main benchmark
Run the exact same seeded synthetic environment for:
- RandomPolicy
- RuleBasedPolicy
- LinUCBPolicy
- IncrementalValuePolicy

Recommended runs:
- smoke test: 1,000 events
- final benchmark: 10 seeds × 10,000 events if runtime permits

### Report
- mean and standard deviation of total recovered revenue
- incremental recovered revenue vs rule baseline
- recovery rate
- net reward
- intervention count
- no-action count
- approval count
- blocked count
- segment-level recovery
- action distribution
- learning curve

Report paired multi-seed variability. Do not hide negative seeds or cold-start underperformance.

### Claim rule
No number enters the pitch unless it is produced by the benchmark script.

## 12. Razorpay demo flow

1. Create a Test Mode failed-payment/recovery scenario.
2. Receive event at `/webhooks/razorpay`.
3. Verify signature.
4. Check `x-razorpay-event-id` for idempotency.
5. Normalize event into RecoverIQ case.
6. Build context.
7. Ask recovery policy for recommendation.
8. Apply policy-as-code.
9. If permitted, create Test Mode Payment Link for the demo case.
10. Record action and audit event.
11. Receive later success event / demo outcome.
12. Close case and display recovered amount.

Important:
- Simulator drives large-scale evaluation.
- Razorpay Test Mode proves real integration.
- Do not attempt to create thousands of real Payment Links; current Test Mode documentation states a 30-link-per-business testing limit.

## 13. Dashboard: only four screens

### Screen 1 — Command Center
- revenue at risk
- recovered revenue
- incremental recovered revenue vs rules
- recovery rate
- safety blocks
- model mode

### Screen 2 — Decision Detail
- context
- candidate actions
- selected action
- expected incremental value
- policy result
- reason codes

### Screen 3 — Learning
- cumulative recovered revenue by policy
- recovery rate over interactions
- action mix by segment
- baseline comparison

### Screen 4 — Safety Gauntlet / Audit
- duplicate webhook
- already-paid event
- opt-out
- amount threshold
- max retries
- invalid signature
- result + reason

## 14. Must-have demo cases

1. **Successful recovery**
   - failed ₹4,999 payment
   - Payment Link selected
   - policy allows
   - test flow succeeds
   - recovered amount appears in dashboard

2. **No-action case**
   - high natural recovery probability
   - low incremental uplift
   - RecoverIQ chooses NO_ACTION

3. **Human approval case**
   - ₹25,000 case
   - model recommends payment action
   - policy requires approval

4. **Duplicate webhook**
   - same event ID twice
   - second is ignored
   - zero duplicate action

5. **Terminal recovered case**
   - already recovered
   - action blocked

## 15. Explicitly cut from V1

- LLM decisioning
- voice/Hinglish agent
- WhatsApp integration
- deep reinforcement learning
- production money movement
- multi-tenant merchant administration
- sophisticated causal inference claims from real-world observational data
- fancy design system

## 16. Submission headline template

Do not fill numbers until final experiment.

> Across **N** simulated revenue-at-risk journeys, RecoverIQ recovered **₹X**, delivering **Y% incremental recovery over the static-rule baseline**, while the policy engine produced **0 unauthorized recovery actions**. The same decision flow is demonstrated against Razorpay Test Mode with signed webhook handling, idempotency, audit trails and bounded execution.
