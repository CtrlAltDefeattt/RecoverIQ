from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RecoveryAction(str, Enum):
    NO_ACTION = "NO_ACTION"
    REMINDER = "REMINDER"
    RETRY_24H = "RETRY_24H"
    PAYMENT_LINK = "PAYMENT_LINK"
    ALT_PAYMENT = "ALT_PAYMENT"
    PARTIAL_PAYMENT = "PARTIAL_PAYMENT"


class PolicyDecision(str, Enum):
    ALLOW = "ALLOW"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    BLOCK = "BLOCK"


@dataclass
class RecoveryContext:
    case_id: str
    customer_id: str
    amount_paise: int
    segment: str
    failure_reason: str
    payment_method: str
    lifetime_value_paise: int
    tenure_days: int
    historical_success_rate: float
    prior_recovery_success_rate: float
    attempts: int
    contacts_last_7d: int
    hours_since_failure: float
    opted_out: bool = False
    already_recovered: bool = False
    duplicate_event: bool = False

    def features(self) -> list[float]:
        segments = ["LOYAL_SAAS", "NEW_ECOM", "PRICE_SENSITIVE", "RETRY_PRONE"]
        failures = [
            "INSUFFICIENT_FUNDS",
            "AUTHENTICATION_FAILED",
            "BANK_DECLINED",
            "NETWORK_ERROR",
        ]
        methods = ["card", "upi", "netbanking", "wallet"]

        numeric = [
            1.0,
            min(self.amount_paise / 2_000_000, 1.0),
            min(self.lifetime_value_paise / 10_000_000, 1.0),
            min(self.tenure_days / 1000, 1.0),
            self.historical_success_rate,
            self.prior_recovery_success_rate,
            min(self.attempts / 3, 1.0),
            min(self.contacts_last_7d / 3, 1.0),
            min(self.hours_since_failure / 72, 1.0),
        ]
        segment_one_hot = [1.0 if self.segment == s else 0.0 for s in segments]
        failure_one_hot = [1.0 if self.failure_reason == f else 0.0 for f in failures]
        method_one_hot = [1.0 if self.payment_method == m else 0.0 for m in methods]
        return numeric + segment_one_hot + failure_one_hot + method_one_hot



@dataclass
class SafetyResult:
    decision: PolicyDecision
    reason: str


@dataclass
class RecoveryOutcome:
    recovered: bool
    recovered_amount_paise: int
    reward_paise: int
    action: RecoveryAction
    policy_decision: PolicyDecision
    policy_reason: str
    executed: bool
    outcome_observed: bool
