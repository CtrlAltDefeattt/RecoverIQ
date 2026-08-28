# Day 7 — Reviewer Dashboard

Day 7 turns RecoverIQ's committed engineering artifacts into a compact,
reviewer-facing operational product. The interface is intentionally a working
surface rather than a marketing landing page.

## Live dashboard

https://recoveriq-command-center.vitkarprajwal.chatgpt.site

## Screen contract

| Screen | Primary reviewer question | Evidence shown |
|---|---|---|
| Command Center | What is happening now? | 500 bounded journeys, outcome distribution, recovered amount, ₹50 batch budget and priority queue |
| Decision Detail | Why this action? | Natural/action probabilities, uplift, expected value, alternatives, guardrails and transition trace |
| Learning Lab | Does learning beat rules consistently? | 10 paired seeds, 9.61% mean gain, 7.47–11.75% interval, 10/10 wins and calibration |
| Safety & Audit | Can unsafe or duplicate work happen? | 7/7 persisted scenarios, ledger counts and exactly-once execution sequence |

## Backend data boundary

The client loads `GET /api/dashboard` and renders the returned read model. This
keeps operational values out of presentation components and provides explicit
loading and failure states. The response declares its RecoveryGym seed and
synthetic source; the interface repeats the limitation around estimated value.

The current route packages committed, deterministic artifacts for the demo.
The production evolution is to compose the same read model from the FastAPI
service, SQLite case/audit tables and experiment result store.

## Experience design

- Dark operator-console visual language with cyan signal and emerald safety states
- Responsive off-canvas sidebar and four keyboard-accessible navigation targets
- Shadcn sidebar, tabs, table, progress and badge primitives
- Dense evidence hierarchy without decorative imagery
- Mobile table overflow, readable status badges and explicit synthetic labels

## Quality gates

```text
Production Vinext build: pass
ESLint: pass
Frontend contract tests: 5 / 5 pass
Routes: / and /api/dashboard
```

The dashboard is read-only. It does not expose secrets, trigger Razorpay calls,
or change the Shadow/Assisted/Autonomous mode.
