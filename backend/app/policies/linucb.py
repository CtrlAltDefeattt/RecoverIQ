from __future__ import annotations

import numpy as np

from backend.app.domain.models import RecoveryAction, RecoveryContext
from backend.app.policies.base import RecoveryPolicy


class LinUCBPolicy(RecoveryPolicy):
    """Lightweight contextual bandit for V1."""

    def __init__(self, alpha: float = 1.0, reward_scale_paise: float = 1_000_000):
        self.actions = list(RecoveryAction)
        self.alpha = alpha
        self.reward_scale_paise = reward_scale_paise
        self.d = 21
        self.A = {a: np.identity(self.d, dtype=float) for a in self.actions}
        self.b = {a: np.zeros((self.d, 1), dtype=float) for a in self.actions}

    def select_action(
        self,
        ctx: RecoveryContext,
        allowed_actions: list[RecoveryAction] | None = None,
    ) -> RecoveryAction:
        x = np.asarray(ctx.features(), dtype=float).reshape(-1, 1)
        scores = {}
        candidates = allowed_actions if allowed_actions is not None else self.actions
        if not candidates:
            raise ValueError("No eligible recovery actions")
        for action in candidates:
            A_inv = np.linalg.inv(self.A[action])
            theta = A_inv @ self.b[action]
            mean = float((theta.T @ x).item())
            uncertainty = self.alpha * float(np.sqrt((x.T @ A_inv @ x).item()))
            scores[action] = mean + uncertainty
        return max(scores, key=scores.get)

    def update(
        self,
        ctx: RecoveryContext,
        action: RecoveryAction,
        reward_paise: int,
    ) -> None:
        x = np.asarray(ctx.features(), dtype=float).reshape(-1, 1)
        reward = reward_paise / self.reward_scale_paise
        self.A[action] += x @ x.T
        self.b[action] += reward * x
