import random

from backend.app.domain.models import RecoveryAction, RecoveryContext
from backend.app.policies.base import RecoveryPolicy

ACTIONS = list(RecoveryAction)


class RandomPolicy(RecoveryPolicy):
    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def select_action(
        self,
        ctx: RecoveryContext,
        allowed_actions: list[RecoveryAction] | None = None,
    ) -> RecoveryAction:
        candidates = allowed_actions if allowed_actions is not None else ACTIONS
        if not candidates:
            raise ValueError("No eligible recovery actions")
        return self.rng.choice(candidates)


class RuleBasedPolicy(RecoveryPolicy):
    def select_action(
        self,
        ctx: RecoveryContext,
        allowed_actions: list[RecoveryAction] | None = None,
    ) -> RecoveryAction:
        candidates = allowed_actions if allowed_actions is not None else ACTIONS
        if not candidates:
            raise ValueError("No eligible recovery actions")

        if ctx.already_recovered:
            proposed = RecoveryAction.NO_ACTION
        elif (
            ctx.failure_reason == "INSUFFICIENT_FUNDS"
            and ctx.attempts < 2
            and ctx.hours_since_failure >= 12
        ):
            proposed = RecoveryAction.RETRY_24H
        elif ctx.failure_reason == "AUTHENTICATION_FAILED":
            proposed = RecoveryAction.ALT_PAYMENT
        elif ctx.segment == "PRICE_SENSITIVE" and ctx.amount_paise >= 500_000:
            proposed = RecoveryAction.PARTIAL_PAYMENT
        elif ctx.historical_success_rate >= 0.9 and ctx.hours_since_failure < 6:
            proposed = RecoveryAction.NO_ACTION
        else:
            proposed = RecoveryAction.PAYMENT_LINK

        if proposed in candidates:
            return proposed
        if RecoveryAction.NO_ACTION in candidates:
            return RecoveryAction.NO_ACTION
        return candidates[0]
