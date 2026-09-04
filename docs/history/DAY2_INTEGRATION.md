# Day 2 — Razorpay Integration

> Historical snapshot: the Render staging plan below was superseded by the
> current Vercel and Neon deployment. See [`../DEPLOYMENT.md`](../DEPLOYMENT.md)
> for the active runbook.

## Implemented

- HMAC-SHA256 verification against the unmodified webhook body
- Required `x-razorpay-event-id` handling
- `payment.failed` and `payment.captured` normalization
- Duplicate delivery protection for the running API process
- Captured-first and failed-then-captured state handling
- Rule-policy recommendation through the safety engine
- Shadow, Assisted and Autonomous mode gates
- Explicit live-execution kill switch
- Standard/partial Payment Link creation
- Payment Link email/SMS notification call
- Readiness endpoint that exposes configuration booleans, never secrets
- Render deployment blueprint
- Test Mode-only smoke script

## Safety defaults

```text
RECOVERIQ_MODE=shadow
RECOVERIQ_EXECUTE_RAZORPAY_ACTIONS=false
```

Both settings must be changed before the adapter can execute a recovery action.
The API also requires configured Razorpay API credentials. High-value actions
remain approval-gated by the policy engine.

## Local configuration

Copy `.env.example` to `.env` and enter Razorpay **Test Mode** values locally:

```text
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
RAZORPAY_WEBHOOK_SECRET=...
```

Never commit `.env`, paste secrets into issues, or include them in screenshots.

## Test Mode smoke call

The following creates a ₹1 Standard Payment Link in Test Mode:

```bash
python -m scripts.razorpay_test_mode_smoke --amount-paise 100
```

The script refuses non-Test key IDs and prints only the created link metadata.

## Public staging webhook

1. Deploy the repository using `render.yaml`.
2. Store the three Razorpay values as secret environment variables in Render.
3. Confirm `GET /readiness` reports webhook and API configuration as true.
4. Configure this Razorpay Test Mode URL:

   ```text
   https://<service-host>/webhooks/razorpay
   ```

5. Subscribe to `payment.failed` and `payment.captured`.
6. Keep RecoverIQ in Shadow Mode for the first genuine events.
7. Confirm duplicate delivery and captured-after-failure behavior in the API logs.

## Honest Day-2 boundary

The integration logic is locally verified with mock Razorpay HTTP transport and
signed API tests. A genuine Razorpay webhook and Payment Link have not been
claimed until account Test Mode credentials are configured and the resulting
IDs are recorded. Event and case state are still process-local; durable SQLite
state and an execution outbox are the persistence milestone.
