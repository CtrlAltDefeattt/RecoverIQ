# Day 10 — Neon production persistence

Day 10 replaces Vercel's ephemeral SQLite fallback with a dedicated Neon
Postgres ledger. The API remains on Vercel; only its durable state moves to
managed Postgres.

## Runtime selection

| Environment | Backend | Configuration |
|---|---|---|
| Vercel production | Neon Postgres | pooled `DATABASE_URL` |
| Local development | SQLite | `RECOVERIQ_DATABASE_PATH` |
| CI | SQLite | temporary test paths |

The webhook route fails with `503` on Vercel when `DATABASE_URL` is missing.
This prevents a correctly signed webhook from being acknowledged after writing
state that could disappear with the function instance.

## Durable schema

The Postgres schema preserves the Day-6 contract across seven tables:
`schema_meta`, `webhook_events`, `recovery_cases`, `decisions`, `actions`,
`outcomes`, and `audit_log`. Database constraints enforce event identity,
payment case identity, one decision per event, one action per decision, and
unique action idempotency keys.

Postgres event claims use `INSERT ... ON CONFLICT DO NOTHING`. Case transitions
use transactions and row locks, while recovery capture remains terminal. The
repository opens short-lived connections through Neon's pooled endpoint, which
is appropriate for Vercel's serverless request lifecycle.

## Migration verification

The schema is maintained in `backend/app/storage/postgres_schema.sql`. Before
promotion it is applied to a Neon temporary branch and checked for:

- all seven tables and four application indexes;
- schema version 1;
- duplicate event rejection;
- one persisted decision, action, and audit transition for a synthetic case;
- a conditional repository contract test for an accessible Neon test branch.

No Neon connection string is committed. Production receives it only through
the `recoveriq-api` Vercel environment settings.
