from __future__ import annotations
import math
import random
import hashlib

from backend.app.domain.models import (
    PolicyDecision,
    RecoveryAction,
    RecoveryContext,
    RecoveryOutcome,
)
from backend.app.safety.engine import SafetyEngine

SEGMENTS = ["LOYAL_SAAS", "NEW_ECOM", "PRICE_SENSITIVE", "RETRY_PRONE"]
FAILURES = [
    "INSUFFICIENT_FUNDS",
    "AUTHENTICATION_FAILED",
    "BANK_DECLINED",
    "NETWORK_ERROR",
]
METHODS = ["card", "upi", "netbanking", "wallet"]

ACTION_COST_PAISE = {
    RecoveryAction.NO_ACTION: 0,
    RecoveryAction.REMINDER: 100,
    RecoveryAction.RETRY_24H: 200,
    RecoveryAction.PAYMENT_LINK: 300,
    RecoveryAction.ALT_PAYMENT: 300,
    RecoveryAction.PARTIAL_PAYMENT: 400,
}

SEGMENT_ACTION_LIFT = {
    "LOYAL_SAAS": {
        RecoveryAction.NO_ACTION: 0.00,
        RecoveryAction.REMINDER: 0.04,
        RecoveryAction.RETRY_24H: 0.09,
        RecoveryAction.PAYMENT_LINK: 0.12,
        RecoveryAction.ALT_PAYMENT: 0.22,
        RecoveryAction.PARTIAL_PAYMENT: 0.06,
    },
    "NEW_ECOM": {
        RecoveryAction.NO_ACTION: 0.00,
        RecoveryAction.REMINDER: 0.22,
        RecoveryAction.RETRY_24H: 0.07,
        RecoveryAction.PAYMENT_LINK: 0.14,
        RecoveryAction.ALT_PAYMENT: 0.08,
        RecoveryAction.PARTIAL_PAYMENT: 0.04,
    },
    "PRICE_SENSITIVE": {
        RecoveryAction.NO_ACTION: 0.00,
        RecoveryAction.REMINDER: 0.08,
        RecoveryAction.RETRY_24H: 0.04,
        RecoveryAction.PAYMENT_LINK: 0.15,
        RecoveryAction.ALT_PAYMENT: 0.07,
        RecoveryAction.PARTIAL_PAYMENT: 0.30,
    },
    "RETRY_PRONE": {
        RecoveryAction.NO_ACTION: 0.00,
        RecoveryAction.REMINDER: 0.06,
        RecoveryAction.RETRY_24H: 0.28,
        RecoveryAction.PAYMENT_LINK: 0.10,
        RecoveryAction.ALT_PAYMENT: 0.11,
        RecoveryAction.PARTIAL_PAYMENT: 0.05,
    },
}


class RecoveryGym:
    """Synthetic environment with hidden correlated response behavior."""

    def __init__(self, seed: int = 42, safety_engine: SafetyEngine | None = None):
        self.seed = seed
        self.safety = safety_engine or SafetyEngine()

    def sample_context(self, event_index: int = 0) -> RecoveryContext:
        rng = random.Random(self.seed + event_index * 1_000_003)
        segment = rng.choices(
            SEGMENTS, weights=[0.25, 0.35, 0.20, 0.20], k=1
        )[0]

        if segment == "LOYAL_SAAS":
            ltv = rng.randint(2_000_000, 12_000_000)
            tenure = rng.randint(180, 1400)
            hist = rng.uniform(0.78, 0.98)
            prior = rng.uniform(0.55, 0.90)
        elif segment == "NEW_ECOM":
            ltv = rng.randint(50_000, 1_500_000)
            tenure = rng.randint(1, 120)
            hist = rng.uniform(0.45, 0.82)
            prior = rng.uniform(0.25, 0.60)
        elif segment == "PRICE_SENSITIVE":
            ltv = rng.randint(300_000, 4_000_000)
            tenure = rng.randint(30, 800)
            hist = rng.uniform(0.55, 0.88)
            prior = rng.uniform(0.30, 0.70)
        else:
            ltv = rng.randint(400_000, 5_000_000)
            tenure = rng.randint(60, 1000)
            hist = rng.uniform(0.60, 0.92)
            prior = rng.uniform(0.40, 0.78)

        amount = int(
            max(
                10_000,
                min(
                    rng.lognormvariate(math.log(180_000), 0.85),
                    5_000_000,
                ),
            )
        )

        failure = rng.choice(FAILURES)
        if segment == "RETRY_PRONE" and rng.random() < 0.55:
            failure = "INSUFFICIENT_FUNDS"
        if segment == "NEW_ECOM" and rng.random() < 0.40:
            failure = "AUTHENTICATION_FAILED"

        return RecoveryContext(
            case_id=f"case_{self.seed}_{event_index}",
            customer_id=f"cust_{self.seed}_{event_index}",
            amount_paise=amount,
            segment=segment,
            failure_reason=failure,
            payment_method=rng.choice(METHODS),
            lifetime_value_paise=ltv,
            tenure_days=tenure,
            historical_success_rate=hist,
            prior_recovery_success_rate=prior,
            attempts=rng.randint(0, 2),
            contacts_last_7d=rng.randint(0, 2),
            hours_since_failure=rng.uniform(0, 72),
            opted_out=rng.random() < 0.03,
            already_recovered=False,
            duplicate_event=False,
        )

    def natural_recovery_probability(self, ctx: RecoveryContext) -> float:
        p = 0.08 + 0.35 * ctx.historical_success_rate
        if ctx.segment == "LOYAL_SAAS":
            p += 0.12
        elif ctx.segment == "NEW_ECOM":
            p -= 0.08
        if ctx.failure_reason == "NETWORK_ERROR":
            p += 0.10
        elif ctx.failure_reason == "BANK_DECLINED":
            p -= 0.07
        if ctx.attempts >= 2:
            p -= 0.06
        return max(0.03, min(p, 0.82))

    def success_probability(
        self,
        ctx: RecoveryContext,
        action: RecoveryAction,
    ) -> float:
        p = self.natural_recovery_probability(ctx)
        p += SEGMENT_ACTION_LIFT[ctx.segment][action]

        if (
            ctx.failure_reason == "INSUFFICIENT_FUNDS"
            and action == RecoveryAction.RETRY_24H
        ):
            p += 0.10
        if (
            ctx.failure_reason == "AUTHENTICATION_FAILED"
            and action == RecoveryAction.ALT_PAYMENT
        ):
            p += 0.14
        if (
            ctx.amount_paise >= 700_000
            and action == RecoveryAction.PARTIAL_PAYMENT
        ):
            p += 0.08
        if ctx.contacts_last_7d >= 2 and action == RecoveryAction.REMINDER:
            p -= 0.12

        return max(0.01, min(p, 0.95))

    def step(
        self,
        ctx: RecoveryContext,
        action: RecoveryAction,
    ) -> RecoveryOutcome:
        safety = self.safety.evaluate(ctx, action)

        if safety.decision in {
            PolicyDecision.BLOCK,
            PolicyDecision.REQUIRE_APPROVAL,
        }:
            return RecoveryOutcome(
                recovered=False,
                recovered_amount_paise=0,
                reward_paise=0,
                action=action,
                policy_decision=safety.decision,
                policy_reason=safety.reason,
                executed=False,
                outcome_observed=False,
            )

        probability = self.success_probability(ctx, action)
        digest = hashlib.sha256(
            f"{self.seed}:{ctx.case_id}:{action.value}".encode("utf-8")
        ).digest()
        u = int.from_bytes(digest[:8], "big") / 2**64
        recovered = u < probability
        amount = ctx.amount_paise if recovered else 0
        fatigue_penalty = (
            100 * ctx.contacts_last_7d
            if action == RecoveryAction.REMINDER
            else 0
        )
        reward = amount - ACTION_COST_PAISE[action] - fatigue_penalty

        return RecoveryOutcome(
            recovered=recovered,
            recovered_amount_paise=amount,
            reward_paise=reward,
            action=action,
            policy_decision=safety.decision,
            policy_reason=safety.reason,
            executed=True,
            outcome_observed=True,
        )
