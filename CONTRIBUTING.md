# Contributing

RecoverIQ is maintained as a focused buildathon project. Changes should preserve
the separation between adaptive decisioning, deterministic safety, execution,
and evaluator-only counterfactuals.

## Development checks

Before opening a pull request, run:

```bash
pip install -r requirements.txt -r requirements-dev.txt
python -m scripts.check_repo_hygiene
python -m pytest -q

cd frontend
npm ci
npm run check
```

## Pull requests

- Keep changes scoped and explain the user-visible or safety impact.
- Add tests for policy, ordering, persistence, or API behaviour changes.
- Never expose unselected potential outcomes to a learning policy.
- Keep money-path decisions deterministic at the final safety boundary.
- Do not commit secrets, local databases, deployment metadata, or reusable
  Payment Link URLs.
- Label simulated results explicitly and avoid merchant-uplift claims without a
  controlled production experiment.
