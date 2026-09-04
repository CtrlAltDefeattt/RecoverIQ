from copy import deepcopy
from pathlib import Path

import pytest

from backend.app.simulator.benchmark import multiseed_benchmark
from backend.app.simulator.charts import render_final_charts
from backend.app.simulator.reporting import (
    build_final_report,
    canonical_config_digest,
    distribution_summary,
    validate_final_config,
)

FROZEN_CONFIG = {
    "benchmark_id": "recoveriq-day8-final-v1",
    "events_per_seed": 20,
    "seed_count": 30,
    "seed_start": 0,
    "workers": 1,
    "linucb_alpha": 0.8,
    "incremental_value_training": {
        "history_events": 6000,
        "history_seed": 20260829,
        "epochs": 4,
    },
    "confidence_level": 0.95,
    "synthetic_only": True,
}


def test_distribution_summary_reports_negative_seeds_and_quartiles():
    summary = distribution_summary([-4.0, -1.0, 2.0, 7.0, 11.0])

    assert summary["negative_count"] == 2
    assert summary["positive_count"] == 3
    assert summary["median"] == 2.0
    assert summary["q1"] == -1.0
    assert summary["q3"] == 7.0


def test_frozen_config_validation_and_digest_are_deterministic():
    validate_final_config(FROZEN_CONFIG)
    reordered = dict(reversed(list(FROZEN_CONFIG.items())))

    assert canonical_config_digest(FROZEN_CONFIG) == canonical_config_digest(
        reordered
    )

    changed = deepcopy(FROZEN_CONFIG)
    changed["seed_count"] = 29
    with pytest.raises(ValueError, match="at least 30 seeds"):
        validate_final_config(changed)


def test_day8_report_and_charts_keep_every_seed(tmp_path: Path):
    raw = multiseed_benchmark(events=20, seeds=30)
    report = build_final_report(raw, FROZEN_CONFIG)

    assert len(report["seed_comparisons"]["incremental_value"]) == 30
    assert report["variability"][
        "incremental_value_relative_gain_pct_vs_rules"
    ]["n"] == 30
    assert report["claim_guardrail"].startswith("Synthetic paired")

    chart_paths = render_final_charts(report, tmp_path)
    assert len(chart_paths) == 3
    for path in chart_paths:
        content = path.read_text(encoding="utf-8")
        assert content.startswith("<svg")
        assert "Synthetic paired evaluation" in content


def test_parallel_multiseed_matches_sequential_execution():
    sequential = multiseed_benchmark(events=10, seeds=2, workers=1)
    parallel = multiseed_benchmark(events=10, seeds=2, workers=2)

    assert parallel == sequential
