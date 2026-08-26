# Architecture

```text
Razorpay Test Mode / RecoveryGym
             |
             v
      Event Ingestion
             |
 Signature / Event-ID Dedup
             |
      Event Normalizer
 (failed / captured / ignored)
             |
             v
       Context Builder
             |
             v
   Adaptive Recovery Policy
 (Random / Rules / LinUCB)
             |
         proposal
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

## Day-2 terminal-state rule

`payment.captured` is terminal for the payment ID. If a late or out-of-order
`payment.failed` event arrives afterward, RecoverIQ records it as stale and does
not reopen or execute recovery. This matches Razorpay's documented possibility
of a failed event being followed by capture for the same transaction.

The current event and case stores are in memory. Durable uniqueness, atomic
state transitions and an execution outbox are intentionally scheduled for the
persistence milestone.
