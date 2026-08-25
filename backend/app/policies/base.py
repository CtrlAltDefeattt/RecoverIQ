from abc import ABC, abstractmethod
from backend.app.domain.models import RecoveryAction, RecoveryContext


class RecoveryPolicy(ABC):
    @abstractmethod
    def select_action(
        self,
        ctx: RecoveryContext,
        allowed_actions: list[RecoveryAction] | None = None,
    ) -> RecoveryAction:
        raise NotImplementedError

    def update(
        self,
        ctx: RecoveryContext,
        action: RecoveryAction,
        reward_paise: int,
    ) -> None:
        return None
