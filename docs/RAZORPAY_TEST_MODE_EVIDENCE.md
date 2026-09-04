# Razorpay Test Mode integration evidence

Verified on September 4, 2026. Both checks used Razorpay Test Mode; no live
charge or production money movement occurred.

## Incoming webhook path

```text
Razorpay Test Mode payment.failed
  → public Vercel webhook
  → raw-body HMAC validation
  → recovery decision
  → Neon Postgres ledger and audit trail
```

| Evidence | Verified value |
|---|---|
| Event ID | `TXsVF0xwZ2tUAr` |
| Event type | `payment.failed` |
| Processing status | `PROCESSED` |
| Recommended action | `PAYMENT_LINK` |
| Policy decision | `ALLOW` |
| Execution status | `shadow_logged` |
| Audit records | 5 |

The persisted audit sequence is `EVENT_RECEIVED`, `CASE_OPENED`,
`DECISION_RECORDED`, `ACTION_RECORDED`, `EVENT_COMPLETED`.

## Outgoing Payment Link API path

The manual GitHub Actions workflow invoked the committed
`RazorpayAdapter.create_payment_link` implementation using encrypted Test Mode
repository secrets.

| Evidence | Verified value |
|---|---|
| Workflow | `Razorpay Test Mode Smoke` |
| Workflow run | [33858565099](https://github.com/CtrlAltDefeattt/RecoverIQ/actions/runs/33858565099) |
| Amount | 100 paise (₹1) |
| Payment Link ID | `plink_TXuWfcOQDHt6zg` |
| Razorpay status | `created` |
| Reference ID | `recoveriq-smoke-1788514198` |

The reusable short URL is intentionally excluded from the repository. The
workflow refuses API key IDs that do not start with `rzp_test_` and never prints
the key ID or secret.

## What this proves

- Razorpay can deliver a genuine signed Test Mode payment event to the public
  RecoverIQ deployment.
- Vercel can validate, process and durably persist the event in Neon Postgres.
- The committed Razorpay adapter can authenticate to the Test Mode API and
  create a Standard Payment Link.
- Shadow Mode prevents the incoming event from autonomously creating another
  link during verification.

This evidence proves integration behavior only. The benchmark remains
synthetic and is not presented as measured merchant uplift.
