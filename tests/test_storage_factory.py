from backend.app.storage.factory import create_recovery_repository
from backend.app.storage.postgres import PostgresRecoveryRepository
from backend.app.storage.sqlite import SQLiteRecoveryRepository


def test_factory_prefers_postgres_when_database_url_is_configured(tmp_path):
    repository = create_recovery_repository(
        database_url="postgresql://example.invalid/recoveriq",
        database_path=str(tmp_path / "ignored.sqlite3"),
    )

    assert isinstance(repository, PostgresRecoveryRepository)


def test_factory_keeps_sqlite_for_local_development(tmp_path):
    repository = create_recovery_repository(
        database_url="",
        database_path=str(tmp_path / "recoveriq.sqlite3"),
    )

    assert isinstance(repository, SQLiteRecoveryRepository)
    repository.close()
