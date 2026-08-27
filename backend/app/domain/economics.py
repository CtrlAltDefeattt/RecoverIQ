from backend.app.domain.models import RecoveryAction, RecoveryContext


BASE_ACTION_COST_PAISE = {
    RecoveryAction.NO_ACTION: 0,
    RecoveryAction.REMINDER: 100,
    RecoveryAction.RETRY_24H: 200,
    RecoveryAction.PAYMENT_LINK: 300,
    RecoveryAction.ALT_PAYMENT: 300,
    RecoveryAction.PARTIAL_PAYMENT: 400,
}


def intervention_cost_paise(
    ctx: RecoveryContext,
    action: RecoveryAction,
) -> int:
    contact_fatigue_cost = (
        100 * ctx.contacts_last_7d
        if action == RecoveryAction.REMINDER
        else 0
    )
    return BASE_ACTION_COST_PAISE[action] + contact_fatigue_cost
