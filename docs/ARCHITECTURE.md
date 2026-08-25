# Architecture

```text
Razorpay Test Mode / RecoveryGym
             |
             v
      Event Ingestion
             |
      Signature / Dedup
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
