# RecoverIQ roadmap

RecoverIQ is an early-stage open-source reference implementation. This roadmap
describes current maintenance priorities; it is not a promise of delivery or a
production-readiness claim.

## Current priorities

### Reliability and safety

- Add a transactional outbox for crash-safe execution handoff.
- Expand property-based tests for idempotency, event ordering, journey limits,
  and terminal-state transitions.
- Define retention, redaction, and encrypted-field boundaries for sensitive
  payment metadata.
- Add authenticated, least-privilege operator access to the dashboard.

### Evaluation

- Publish additional reproducible baselines and calibration diagnostics.
- Add distribution-shift and delayed-feedback scenarios to the simulator.
- Define a merchant holdout protocol before making any causal uplift claim.
- Track policy quality, safety vetoes, contact burden, and cost together.

### Extensibility

- Stabilize the provider-adapter interface.
- Document a fixture-driven guide for adding another payment provider.
- Separate reusable decision/evaluation packages from the demonstration API.

### Maintainer experience

- Expand issue templates and contribution examples.
- Automate dependency and documentation checks in CI.
- Publish versioned releases once the public interfaces stabilize.

## Deliberately out of scope for now

- Autonomous live-money execution without human and deterministic controls.
- Claims of merchant uplift based only on synthetic evaluation.
- Training on unobserved counterfactual outcomes.
- Storage or publication of live customer payment data.

To propose a roadmap change, open a feature request explaining the user need,
safety implications, evaluation plan, and maintenance cost.
