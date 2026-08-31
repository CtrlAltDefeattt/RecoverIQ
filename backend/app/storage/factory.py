from __future__ import annotations

from backend.app.storage.postgres import PostgresRecoveryRepository
from backend.app.storage.sqlite import SQLiteRecoveryRepository


RecoveryRepository = PostgresRecoveryRepository | SQLiteRecoveryRepository


def create_recovery_repository(
    *,
    database_url: str,
    database_path: str,
) -> RecoveryRepository:
    if database_url:
        return PostgresRecoveryRepository(database_url)
    return SQLiteRecoveryRepository(database_path)
