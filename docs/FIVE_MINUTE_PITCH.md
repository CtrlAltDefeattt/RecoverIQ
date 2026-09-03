# Five-minute pitch script

Target length: 4 minutes 40 seconds to 5 minutes. Rehearse once while changing
screens; do not read code during the recording.

| Time | Screen | Speaker script |
|---|---|---|
| 0:00–0:25 | Title / Command Center | “A failed payment is not one problem. Some customers recover naturally, some need a reminder or new payment path, and some should not be contacted at all. Static rules treat those cases too similarly and can waste margin or damage trust.” |
| 0:25–0:55 | One-line thesis | “RecoverIQ is a safety-constrained adaptive revenue-recovery engine. For each failed-payment context it estimates the incremental value of permitted actions, chooses only inside hard operational limits, and learns only from outcomes it actually observed.” |
| 0:55–1:25 | Architecture | “Razorpay Test Mode events or paired RecoveryGym cases enter the same decision flow. The event is validated and claimed exactly once in Neon Postgres. The policy proposes an action; journey limits and the safety engine can allow it, require approval, or block it. Every decision, action and outcome is auditable before anything reaches the Razorpay adapter.” |
| 1:25–2:05 | Command Center | “This command center shows the operating posture: at-risk cases, the two-intervention journey limit, cooldowns, and the shared batch budget. RecoverIQ can explicitly wait or stop; it does not assume that more contact is always better.” |
| 2:05–2:45 | Decision Detail | “For this case, the explanation separates estimated natural recovery from action recovery, then converts their difference into expected incremental net value. The model never sees the simulator’s hidden counterfactual probabilities. Before selection, unsafe actions are masked; after selection, the safety engine performs a final veto.” |
| 2:45–3:15 | Safety & Audit | “The safety gauntlet covers duplicate delivery, opt-out, high-value approval, attempt exhaustion, capture-before-failure, exactly-once execution and audit completeness. All seven persisted scenarios pass. Blocked and approval-pending actions are never mislabeled as customer failures for learning.” |
| 3:15–3:55 | Learning Lab | “The final benchmark uses 30 paired seeds and 10,000 synthetic cases per seed. The incremental-value policy beats fixed rules on all 30 seeds, with an average 11.697 percent simulated recovered-revenue gain. The paired 95 percent interval is 11.350 to 12.043 percent. These are synthetic engineering results, not a claim of merchant uplift.” |
| 3:55–4:25 | API health / Razorpay evidence | “The public FastAPI deployment is connected to a durable Neon ledger; this live health probe performs a real database query. The webhook path verifies the unmodified request body, rejects invalid signatures and ignores duplicate event IDs. Here is the Test Mode delivery and its persisted shadow decision.” |
| 4:25–4:55 | Dashboard overview | “RecoverIQ’s value is not another message channel. It is a measurable control layer over existing recovery primitives: adaptive where evidence supports it, deterministic where safety demands it, and honest about what has only been simulated.” |
| 4:55–5:00 | Title | “RecoverIQ: recover more value, with fewer unsafe interventions.” |

## If genuine Test Mode evidence is not complete

Replace the final sentence in the 3:55–4:25 section with:

> “The production path is verified with a signed synthetic Razorpay-shaped event;
> a genuine Razorpay delivery remains the final credential-dependent check.”

Do not call the synthetic smoke request a real Razorpay event.

## Likely reviewer questions

**Why not an LLM?**  The core decision is a bounded contextual-action problem
with measurable outcomes. Deterministic constraints are easier to audit in the
money path. An LLM could later explain decisions or assist operators without
controlling execution.

**Is the 11.697% real uplift?**  No. It is additional simulated recovered
revenue versus fixed rules in a paired synthetic benchmark. Merchant impact
requires a randomized shadow-to-live evaluation.

**How is exploration made safe?**  Unsafe actions are removed before policy
selection, the selected action receives a final safety review, and production
execution also requires explicit mode and kill-switch settings.

**What survives a serverless restart?**  Webhook claims, cases, decisions,
actions, outcomes and audit records are stored in Neon Postgres with database
uniqueness constraints.

**What would come next?**  Calibrate on merchant shadow traffic, define a
randomized holdout, add approval workflows, and enable Test Mode actions in a
strictly bounded cohort before any live rollout.
