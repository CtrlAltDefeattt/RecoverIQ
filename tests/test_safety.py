from backend.app.domain.models import RecoveryAction, RecoveryContext, PolicyDecision
from backend.app.safety.engine import SafetyEngine
from backend.app.simulator.environment import RecoveryGym


def context(**overrides):
    base = dict(
        case_id="case_1",
        customer_id="cust_1",
        amount_paise=499900,
        segment="LOYAL_SAAS",
        failure_reason="INSUFFICIENT_FUNDS",
        payment_method="card",
        lifetime_value_paise=4000000,
        tenure_days=400,
        historical_success_rate=0.9,
        prior_recovery_success_rate=0.7,
        attempts=1,
        contacts_last_7d=1,
        hours_since_failure=24,
        opted_out=False,
        already_recovered=False,
        duplicate_event=False,
    )
    base.update(overrides)
    return RecoveryContext(**base)


def test_duplicate_is_blocked():
    result = SafetyEngine().evaluate(
        context(duplicate_event=True),
        RecoveryAction.PAYMENT_LINK,
    )
    assert result.decision == PolicyDecision.BLOCK


def test_high_value_requires_approval():
    result = SafetyEngine().evaluate(
        context(amount_paise=2500000),
        RecoveryAction.PAYMENT_LINK,
    )
    assert result.decision == PolicyDecision.REQUIRE_APPROVAL


def test_safe_low_value_is_allowed():
    result = SafetyEngine().evaluate(
        context(),
        RecoveryAction.PAYMENT_LINK,
    )
    assert result.decision == PolicyDecision.ALLOW


def test_blocked_proposal_has_no_observed_outcome():
    outcome = RecoveryGym(seed=42).step(
        context(duplicate_event=True),
        RecoveryAction.PAYMENT_LINK,
    )
    assert outcome.executed is False
    assert outcome.outcome_observed is False


def test_approval_pending_has_no_observed_outcome():
    outcome = RecoveryGym(seed=42).step(
        context(amount_paise=2_500_000),
        RecoveryAction.PAYMENT_LINK,
    )
    assert outcome.policy_decision == PolicyDecision.REQUIRE_APPROVAL
    assert outcome.executed is False
    assert outcome.outcome_observed is False


def test_allowed_action_produces_observed_outcome():
    outcome = RecoveryGym(seed=42).step(
        context(),
        RecoveryAction.PAYMENT_LINK,
    )
    assert outcome.executed is True
    assert outcome.outcome_observed is True


def test_autonomous_action_mask_excludes_approval_and_blocked_actions():
    engine = SafetyEngine()
    high_value_actions = engine.allowed_actions(context(amount_paise=2_500_000))
    opted_out_actions = engine.allowed_actions(context(opted_out=True))

    assert RecoveryAction.PAYMENT_LINK not in high_value_actions
    assert RecoveryAction.PAYMENT_LINK not in opted_out_actions
    assert RecoveryAction.NO_ACTION in high_value_actions
    assert RecoveryAction.NO_ACTION in opted_out_actions


def test_reviewable_mask_keeps_approval_but_excludes_blocked_actions():
    engine = SafetyEngine()
    high_value_actions = engine.reviewable_actions(
        context(amount_paise=2_500_000)
    )
    opted_out_actions = engine.reviewable_actions(context(opted_out=True))

    assert RecoveryAction.PAYMENT_LINK in high_value_actions
    assert RecoveryAction.PAYMENT_LINK not in opted_out_actions
