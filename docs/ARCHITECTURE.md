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
             |
             +----> Policy update
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

## Day-2 terminal-state rule

`payment.captured` is terminal for the payment ID. If a late or out-of-order
`payment.failed` event arrives afterward, RecoverIQ records it as stale and does
not reopen or execute recovery. This matches Razorpay's documented possibility
of a failed event being followed by capture for the same transaction.

The current event and case stores are in memory. Durable uniqueness, atomic
state transitions and an execution outbox are intentionally scheduled for the
persistence milestone.
