# Security policy

## Supported version

RecoverIQ is currently pre-1.0. The `main` branch is the only supported version.

## Reporting a vulnerability

Please do not disclose vulnerabilities, credentials, webhook payloads, or
customer information in a public issue.

Use GitHub's **Security → Report a vulnerability** flow for this repository. A
useful report includes the affected component, reproduction steps, potential
impact, and any suggested mitigation. Do not include live Razorpay keys, webhook
secrets, database URLs, or reusable Payment Link URLs.

## Security posture

- The public deployment runs in Shadow Mode by default.
- External Razorpay execution requires both valid Test Mode credentials and an
  explicit execution switch.
- Webhook signatures are checked against the untouched request body.
- Event IDs and action idempotency keys are enforced in durable storage.
- Secrets are supplied through deployment environment variables and are scanned
  out of repository content by CI.

RecoverIQ is an early-stage reference implementation. It requires authenticated
operator access, a transactional outbox, retention controls, encrypted
sensitive fields, independent security review, and a merchant validation
programme before any live-money rollout.
