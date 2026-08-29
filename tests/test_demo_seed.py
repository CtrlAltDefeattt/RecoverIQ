import asyncio

from scripts.seed_demo_data import seed_demo_data


def test_demo_seed_is_deterministic_and_network_free(tmp_path):
    database = tmp_path / "recoveriq-demo.sqlite3"

    first = asyncio.run(
        seed_demo_data(str(database), cases=12, seed=42, reset=True)
    )
    second = asyncio.run(
        seed_demo_data(str(database), cases=12, seed=42, reset=True)
    )

    assert first == second
    assert first["synthetic"] is True
    assert first["mode"] == "shadow"
    assert first["recovered_cases"] == 4
    assert first["network_calls"] == 0
    assert first["ledger_counts"] == {
        "webhook_events": 16,
        "recovery_cases": 12,
        "decisions": 12,
        "actions": 12,
        "outcomes": 4,
        "audit_log": 72,
    }
