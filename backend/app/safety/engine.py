from backend.app.domain.models import (
    PolicyDecision,
    RecoveryAction,
    RecoveryContext,
    SafetyResult,
)

CONTACT_ACTIONS = {
    RecoveryAction.REMINDER,
    RecoveryAction.PAYMENT_LINK,
    RecoveryAction.ALT_PAYMENT,
    RecoveryAction.PARTIAL_PAYMENT,
}

MONEY_PATH_ACTIONS = {
    RecoveryAction.RETRY_24H,
    RecoveryAction.PAYMENT_LINK,
    RecoveryAction.ALT_PAYMENT,
    RecoveryAction.PARTIAL_PAYMENT,
}


class SafetyEngine:
    def __init__(
        self,
        autonomous_limit_paise: int = 1_000_000,
        max_attempts: int = 3,
        max_contacts_7d: int = 3,
        retry_cooldown_hours: float = 12.0,
    ):
        self.autonomous_limit_paise = autonomous_limit_paise
        self.max_attempts = max_attempts
        self.max_contacts_7d = max_contacts_7d
        self.retry_cooldown_hours = retry_cooldown_hours

    def allowed_actions(self, ctx: RecoveryContext) -> list[RecoveryAction]:
        """Return actions eligible for autonomous execution in this context."""
        return [
            action
            for action in RecoveryAction
            if self.evaluate(ctx, action).decision == PolicyDecision.ALLOW
        ]

    def reviewable_actions(self, ctx: RecoveryContext) -> list[RecoveryAction]:
        """Return actions that are allowed or can be escalated for approval."""
        return [
            action
            for action in RecoveryAction
            if self.evaluate(ctx, action).decision != PolicyDecision.BLOCK
        ]

    def evaluate(self, ctx: RecoveryContext, action: RecoveryAction) -> SafetyResult:
        if ctx.duplicate_event:
            return SafetyResult(PolicyDecision.BLOCK, "DUPLICATE_EVENT")
        if ctx.already_recovered:
            return SafetyResult(PolicyDecision.BLOCK, "ALREADY_RECOVERED")
        if ctx.opted_out and action in CONTACT_ACTIONS:
            return SafetyResult(PolicyDecision.BLOCK, "CUSTOMER_OPT_OUT")
        if ctx.attempts >= self.max_attempts and action != RecoveryAction.NO_ACTION:
            return SafetyResult(PolicyDecision.BLOCK, "MAX_ATTEMPTS_REACHED")
        if ctx.contacts_last_7d >= self.max_contacts_7d and action in CONTACT_ACTIONS:
            return SafetyResult(PolicyDecision.BLOCK, "CONTACT_LIMIT_REACHED")
        if (
            action == RecoveryAction.RETRY_24H
            and ctx.hours_since_failure < self.retry_cooldown_hours
        ):
            return SafetyResult(PolicyDecision.BLOCK, "RETRY_COOLDOWN")
        if (
            ctx.amount_paise > self.autonomous_limit_paise
            and action in MONEY_PATH_ACTIONS
        ):
            return SafetyResult(
                PolicyDecision.REQUIRE_APPROVAL,
                "AMOUNT_ABOVE_AUTONOMOUS_LIMIT",
            )
        return SafetyResult(PolicyDecision.ALLOW, "POLICY_OK")
