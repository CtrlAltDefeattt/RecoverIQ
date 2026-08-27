from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum

from backend.app.domain.models import RecoveryAction, RecoveryContext


class JourneyCommand(str, Enum):
    EXECUTE = "EXECUTE"
    WAIT = "WAIT"
    STOP = "STOP"
    ESCALATE = "ESCALATE"


class JourneyStatus(str, Enum):
    OPEN = "OPEN"
    WAITING = "WAITING"
    RECOVERED = "RECOVERED"
    STOPPED = "STOPPED"
    EXHAUSTED = "EXHAUSTED"
    ESCALATED = "ESCALATED"


TERMINAL_JOURNEY_STATUSES = {
    JourneyStatus.RECOVERED,
    JourneyStatus.STOPPED,
    JourneyStatus.EXHAUSTED,
    JourneyStatus.ESCALATED,
}


@dataclass(frozen=True)
class InterventionRecord:
    sequence: int
    action: RecoveryAction
    executed_at_hours: float
    recovered: bool
    recovered_amount_paise: int
    reward_paise: int
    estimate: dict

    def to_dict(self) -> dict:
        data = asdict(self)
        data["action"] = self.action.value
        return data


@dataclass
class JourneyState:
    journey_id: str
    context: RecoveryContext
    status: JourneyStatus = JourneyStatus.OPEN
    stop_reason: str | None = None
    max_interventions: int = 2
    min_interval_hours: float = 24.0
    interventions: list[InterventionRecord] = field(default_factory=list)

    @property
    def terminal(self) -> bool:
        return self.status in TERMINAL_JOURNEY_STATUSES

    @property
    def last_intervention_at_hours(self) -> float | None:
        if not self.interventions:
            return None
        return self.interventions[-1].executed_at_hours

    def to_dict(self) -> dict:
        return {
            "journey_id": self.journey_id,
            "status": self.status.value,
            "stop_reason": self.stop_reason,
            "max_interventions": self.max_interventions,
            "min_interval_hours": self.min_interval_hours,
            "intervention_count": len(self.interventions),
            "interventions": [record.to_dict() for record in self.interventions],
        }


@dataclass(frozen=True)
class JourneyDecision:
    command: JourneyCommand
    reason: str
    action: RecoveryAction | None = None
    retry_after_hours: float | None = None
    estimate: dict | None = None

    def to_dict(self) -> dict:
        return {
            "command": self.command.value,
            "reason": self.reason,
            "action": self.action.value if self.action else None,
            "retry_after_hours": self.retry_after_hours,
            "estimate": self.estimate,
        }
