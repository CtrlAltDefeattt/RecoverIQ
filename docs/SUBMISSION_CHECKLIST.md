# Final submission checklist

## Code and evidence

- [x] Frozen 30-seed × 10,000-case paired benchmark committed.
- [x] Synthetic claims include variability and limitations.
- [x] Seven-scenario persisted Safety Gauntlet committed.
- [x] Backend and frontend automated tests in GitHub Actions.
- [x] Repository hygiene scan rejects secrets and local database files.
- [x] Architecture diagram and setup instructions committed.
- [x] Five-minute recording script and demo runbook committed.

## Production

- [x] Public dashboard deployed on Vercel.
- [x] Public FastAPI deployment on Vercel.
- [x] Neon Postgres schema migrated and `DATABASE_URL` configured.
- [x] Vercel API connectivity to Neon verified through a persisted production
  webhook transaction.
- [x] Razorpay Test Mode webhook secret configured without exposing its value.
- [x] Genuine `payment.failed` Test Mode webhook delivery persisted in Neon.
- [x] One ₹1 Test Mode Payment Link created through the committed adapter.

## Recording

- [ ] Record at 1080p with readable browser zoom.
- [ ] Keep the recording under five minutes.
- [ ] Show the four dashboard screens, architecture and live database health.
- [ ] Show non-secret Razorpay Test Mode delivery evidence if completed.
- [ ] State that benchmark results are synthetic.
- [ ] State that no production money movement is enabled.
- [ ] Review the final video once for accidental secrets or personal tabs.

## Submission form

- [ ] Confirm the buildathon accepts a private repository. If it does, grant the
  evaluator account access; otherwise make the repository public only when you
  are ready to submit.
- [ ] Add the repository URL.
- [ ] Add the public dashboard URL.
- [ ] Add the public API URL if requested.
- [ ] Upload the video and verify reviewer access in a signed-out window.
- [ ] Add the video URL.
- [ ] Recheck every link from a signed-out window.
- [ ] Submit before the deadline and save the confirmation.

## Final claim

> Across 30 paired synthetic seeds with 10,000 cases each, RecoverIQ's
> incremental-value policy delivered an average 11.697% additional simulated
> recovered revenue versus fixed rules; the paired 95% interval was 11.350% to
> 12.043%, with zero unauthorized actions in the persisted Safety Gauntlet.

Do not remove “synthetic” or rewrite this as proven merchant uplift.
