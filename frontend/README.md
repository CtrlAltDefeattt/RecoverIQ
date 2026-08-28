# RecoverIQ Command Center

The Day-7 frontend is a responsive Vinext/React reviewer dashboard deployed at:

https://recoveriq-command-center.vitkarprajwal.chatgpt.site

## Screens

1. **Command Center** — journey outcomes, recovered value, budget allocation and priority queue.
2. **Decision Detail** — natural recovery, action probability, estimated uplift, value equation and deterministic guardrails.
3. **Learning Lab** — paired confidence interval, seed wins, calibration and observable-model boundary.
4. **Safety & Audit** — seven persisted safety scenarios, SQLite counts and exactly-once execution trace.

All displayed metrics are fetched from `GET /api/dashboard`. Synthetic results
remain explicitly labelled and are not presented as merchant uplift.

## Local development

```bash
npm ci
npm run dev
```

Quality gates:

```bash
npm run lint
npm test
```
