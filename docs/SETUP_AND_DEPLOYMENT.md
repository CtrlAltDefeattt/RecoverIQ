# RecoverIQ setup and deployment

RecoverIQ runs as one Vercel project with two services:

| Route | Runtime | Purpose |
| --- | --- | --- |
| `/` | Next.js / Node.js 22 | Reviewer command center and synthetic dashboard read model |
| `/backend` | FastAPI / Python 3.12 | Health, readiness, simulation, and signed Razorpay webhook endpoints |

The root `vercel.json` is the source of truth for this routing. Keep the Vercel
Framework Preset set to **Services**.

![RecoverIQ architecture](assets/recoveriq-architecture.svg)

## Local setup

Requirements: Python 3.12, Node.js 22.13 or newer, and npm 10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cd frontend
npm ci
npm run lint
npm test
cd ..
python -m pytest -q
python -m scripts.check_repo_hygiene
```

On Windows, activate with `.venv\Scripts\activate`. Run the API with
`uvicorn backend.app.main:app --reload` and the dashboard with `npm run dev`
from `frontend/`.

## Seed deterministic demo data

The seed command creates a synthetic SQLite ledger through the real integration
service in shadow mode. It makes zero Razorpay network calls.

```bash
python -m scripts.seed_demo_data \
  --database data/recoveriq-demo.sqlite3 \
  --cases 12 \
  --seed 42 \
  --output outputs/day9_demo_seed_summary.json
```

The command resets the target ledger by default, so the same seed and case count
produce the same rows and summary. Pass `--append` only to demonstrate duplicate
event handling. SQLite files remain ignored and must not be committed.

## Safe environment baseline

Copy `.env.example` to `.env` locally. For a reviewer deployment, leave all
Razorpay secret values unset and retain:

```dotenv
RECOVERIQ_MODE=shadow
RECOVERIQ_EXECUTE_RAZORPAY_ACTIONS=false
```

Secret values belong in Vercel Project Settings, never in GitHub. Required names
are `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`,
`RECOVERIQ_MODE`, `RECOVERIQ_EXECUTE_RAZORPAY_ACTIONS`,
`RECOVERIQ_AUTONOMOUS_LIMIT_PAISE`, and `RECOVERIQ_DATABASE_PATH`.

The backend automatically uses `/tmp/recoveriq.sqlite3` on Vercel when no path
is configured. That is enough for health checks and a read-only demo, but Vercel
function storage is ephemeral. Do not enable live webhook execution until the
repository uses durable managed storage or a service with a persistent disk.

## Vercel deployment

1. Import the private `CtrlAltDefeattt/RecoverIQ` repository into the intended
   Vercel team.
2. Leave the project root at the repository root.
3. Select the **Services** Framework Preset.
4. Create a preview deployment from `main`.
5. Verify the dashboard and both runtimes before promotion:

```bash
vercel curl / --deployment <preview-url>
vercel curl /api/dashboard --deployment <preview-url>
vercel curl /backend/health --deployment <preview-url>
vercel curl /backend/readiness --deployment <preview-url>
```

Expected readiness in the safe reviewer configuration is `degraded`: the API is
healthy while Razorpay webhook credentials are intentionally absent. Promote the
exact verified artifact with `vercel promote <preview-url>`.

The GitHub repository remains private. Vercel only needs repository installation
access for builds; no source visibility change is required.

## Repository hygiene

`python -m scripts.check_repo_hygiene` runs in CI and rejects tracked environment
files, databases, private keys, common live-token signatures, or missing ignore
rules for local state and Vercel metadata. Never paste secret values into build
logs, issues, screenshots, or documentation.
