# RecoverIQ documentation

This index separates the current system contract from historical build notes so
reviewers can reach the strongest evidence without following the implementation
chronology.

## Start here

| Document | Question answered |
|---|---|
| [Product specification](PRODUCT_SPEC.md) | What is in scope and how is success measured? |
| [Architecture](ARCHITECTURE.md) | How do events, policies, safety, execution, and persistence interact? |
| [Decision model](MODEL.md) | How is incremental value estimated without counterfactual leakage? |
| [Journey orchestration](ORCHESTRATION.md) | How are journeys and batch budgets bounded? |
| [Persistence and safety](PERSISTENCE_AND_SAFETY.md) | How are duplicates, ordering, and unsafe actions prevented? |
| [Evaluation](EVALUATION.md) | What is the frozen evaluation contract and what did it show? |

## Integration and operations

| Document | Purpose |
|---|---|
| [Deployment](DEPLOYMENT.md) | Local setup plus Vercel and Neon configuration |
| [Razorpay Test Mode evidence](RAZORPAY_TEST_MODE_EVIDENCE.md) | Verified incoming webhook and outgoing Payment Link paths |
| [Demo runbook](DEMO_RUNBOOK.md) | Safe, repeatable reviewer walkthrough |

## Submission material

| Document | Purpose |
|---|---|
| [Five-minute pitch](FIVE_MINUTE_PITCH.md) | Timed narration reference |
| [Submission checklist](SUBMISSION_CHECKLIST.md) | Final link, safety, and evidence checks |

## Historical notes

The [`history/`](history/) directory preserves chronological engineering notes
for traceability. Those documents describe intermediate states and are not the
current deployment contract.
