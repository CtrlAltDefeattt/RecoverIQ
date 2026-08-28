import pytest

from experiments.run_day6_safety_gauntlet import run_gauntlet


@pytest.fixture(scope="module")
def gauntlet_report(tmp_path_factory):
    database = tmp_path_factory.mktemp("day6") / "gauntlet.sqlite3"
    return run_gauntlet(str(database))


@pytest.mark.parametrize(
    "scenario",
    [
        "duplicate_event",
        "customer_opt_out",
        "high_value_approval",
        "attempt_limit",
        "already_paid_terminal",
        "exactly_once_execution",
        "audit_completeness",
    ],
)
def test_safety_gauntlet_scenario_passes(gauntlet_report, scenario):
    assert gauntlet_report["scenarios"][scenario]["passed"] is True


def test_safety_gauntlet_never_uses_real_network(gauntlet_report):
    assert gauntlet_report["all_passed"] is True
    assert gauntlet_report["real_network_calls"] == 0
