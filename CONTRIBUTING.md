# Contributing to RecoverIQ

Thank you for helping improve RecoverIQ. The project welcomes focused bug
reports, documentation fixes, tests, evaluation improvements, safety controls,
and provider integrations.

All contributions must preserve the separation between adaptive decisioning,
deterministic safety, execution, and evaluator-only counterfactuals.

## Before you start

- Read the [architecture](docs/ARCHITECTURE.md),
  [evaluation contract](docs/EVALUATION.md), and
  [security policy](SECURITY.md).
- Search existing issues before opening a new one.
- Open an issue before a large change, new dependency, or public API change so
  scope and safety implications can be agreed first.
- Never use a public issue to report a vulnerability or expose credentials.

By participating, you agree to follow the
[Code of Conduct](CODE_OF_CONDUCT.md).

## Local setup

```bash
git clone https://github.com/CtrlAltDefeattt/RecoverIQ.git
cd RecoverIQ

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env

cd frontend
npm ci
```

On Windows, activate the environment with `.venv\Scripts\activate` and copy
`.env.example` to `.env` manually.

The committed configuration is fail-closed. Do not enable external payment
execution while developing or testing a contribution.

## Required checks

Run the backend checks from the repository root:

```bash
python -m scripts.check_repo_hygiene
python -m ruff check .
python -m pytest -q
python -m experiments.run_benchmark --events 1000 --seed 42
```

Run the dashboard checks from `frontend/`:

```bash
npm run lint
npm run typecheck
npm test
```

CI repeats these checks and additional deterministic safety and evaluation
smoke tests on every pull request.

## Pull-request expectations

- Keep changes scoped and explain the user-visible, evaluation, and safety
  impact.
- Add or update tests for policy, ordering, persistence, API, or UI behavior.
- Never expose unselected potential outcomes to a learning policy.
- Keep money-path decisions deterministic at the final safety boundary.
- Preserve idempotency and terminal-state ordering in webhook changes.
- Do not commit secrets, local databases, deployment metadata, customer data,
  or reusable Payment Link URLs.
- Label simulated results explicitly. Do not make merchant-uplift or causal
  production claims without a controlled production experiment.
- Update documentation when behavior, configuration, or public interfaces
  change.

Small pull requests are easier to review. A maintainer may ask for a large
change to be split into independently testable parts.

## Review and decision process

The primary maintainer reviews scope, tests, documentation, and safety impact.
Changes affecting payment execution, learning boundaries, or customer contact
rules require explicit maintainer approval. See [MAINTAINERS.md](MAINTAINERS.md)
for the current governance model.
