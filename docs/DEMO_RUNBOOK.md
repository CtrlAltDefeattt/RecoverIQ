# RecoverIQ demo runbook

Use this runbook for the final screen recording. Keep the API in Shadow Mode so
the demo cannot trigger a real recovery action.

## Public URLs

- Dashboard: <https://recoveriq-dashboard-prajwal-ai.vercel.app>
- API health: <https://recoveriq-api.vercel.app/health>
- Database health: <https://recoveriq-api.vercel.app/health/database>
- Readiness: <https://recoveriq-api.vercel.app/readiness>
- Razorpay webhook: `https://recoveriq-api.vercel.app/webhooks/razorpay`

## One-time secret setup

In the Vercel API project, set the following Production environment variables:

```text
DATABASE_URL=<Neon pooled connection string>
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=<Test Mode API secret>
RAZORPAY_WEBHOOK_SECRET=<same secret configured for the Razorpay webhook>
RECOVERIQ_MODE=shadow
RECOVERIQ_EXECUTE_RAZORPAY_ACTIONS=false
```

Never paste those values into GitHub, screenshots, the recording or chat. After
changing Vercel variables, redeploy the API so the deployment receives them.

In the Razorpay Test Mode dashboard, configure the RecoverIQ webhook URL and
subscribe to `payment.failed` and `payment.captured`.

## Preflight

Run these checks before recording:

```bash
curl -fsS https://recoveriq-api.vercel.app/health
curl -fsS https://recoveriq-api.vercel.app/health/database
curl -fsS https://recoveriq-api.vercel.app/readiness
```

Expected results:

- `/health` returns `status: ok`.
- `/health/database` returns `backend: postgresql` and `reachable: true`.
- `/readiness` reports the Postgres backend and the configuration booleans you
  intentionally enabled. It never returns secret values.

Open the dashboard once and visit all four screens so assets are warm before the
recording.

## Signed production smoke test

This sends a synthetic Razorpay-shaped event signed with the configured webhook
secret. It proves raw-body signature verification, Vercel routing, Neon writes
and duplicate-event protection. It is not described as a genuine Razorpay
delivery.

Set the secret only in the current shell, then run:

```bash
python -m scripts.razorpay_webhook_smoke --verify-idempotency
```

The first response should be `decision_recorded`; the second should be
`duplicate_ignored`. Remove the shell variable after the test.

## Genuine Razorpay Test Mode evidence

1. Keep the API in Shadow Mode.
2. Create one ₹1 Test Mode Payment Link through the committed adapter:

   ```bash
   python -m scripts.razorpay_test_mode_smoke --amount-paise 100
   ```

3. Use Razorpay Test Mode to generate one subscribed payment event. Do not use a
   live key or a real charge.
4. Confirm a successful delivery in the Razorpay webhook delivery view.
5. Confirm the event, case, decision/action and audit rows in the Neon console.
6. Record only non-secret evidence: event type, event ID, processing status,
   decision, execution status and timestamps.

This is the only step that can truthfully be called a genuine Razorpay Test Mode
integration exercise.

### Verified Test Mode receipt — September 4, 2026

The production webhook received and processed one genuine Razorpay Test Mode
`payment.failed` event:

- Event ID: `TXsVF0xwZ2tUAr`
- Processing status: `PROCESSED`
- Recommended action: `PAYMENT_LINK`
- Policy decision: `ALLOW`
- Execution status: `shadow_logged`
- Durable audit sequence: `EVENT_RECEIVED`, `CASE_OPENED`,
  `DECISION_RECORDED`, `ACTION_RECORDED`, `EVENT_COMPLETED`

This receipt proves Razorpay Test Mode → public Vercel webhook → signature
validation → recovery decision → Neon Postgres persistence. Shadow Mode ensured
that no external recovery action or real money movement occurred.

## Recording order

1. Problem and one-line thesis.
2. Architecture diagram in the README.
3. Command Center and bounded journey/budget controls.
4. Decision Detail and safety gate.
5. Learning Lab benchmark and confidence interval.
6. Safety & Audit screen.
7. API database health and readiness JSON.
8. Genuine Razorpay delivery evidence, if completed.
9. Limitations and closing statement.

## Recording safety

- Use an incognito browser profile with bookmarks hidden.
- Close Vercel, Neon and Razorpay settings pages before recording.
- Never show environment-variable values, connection strings or API keys.
- Say “simulated” whenever quoting benchmark results.
- Do not say the system has produced real merchant uplift.
- If genuine Test Mode evidence is not complete, say so plainly and show the
  signed production smoke test instead.
