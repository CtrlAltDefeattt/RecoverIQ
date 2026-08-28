from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.app.simulator.benchmark import multiseed_benchmark
from backend.app.simulator.charts import render_final_charts
from backend.app.simulator.reporting import build_final_report, validate_final_config


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="experiments/configs/day8_final.json",
    )
    parser.add_argument(
        "--output",
        default="outputs/day8_final_10k_x_30.json",
    )
    parser.add_argument(
        "--charts-dir",
        default="outputs/day8_charts",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    validate_final_config(config)
    print(
        "Running frozen Day 8 benchmark: "
        f'{config["seed_count"]} paired seeds × '
        f'{config["events_per_seed"]:,} cases with '
        f'{config["workers"]} workers',
        flush=True,
    )

    summary = multiseed_benchmark(
        events=config["events_per_seed"],
        seeds=config["seed_count"],
        workers=config["workers"],
    )
    report = build_final_report(summary, config)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    chart_paths = render_final_charts(report, Path(args.charts_dir))

    comparison = report["paired_policy_comparison"]
    variability = report["variability"][
        "incremental_value_relative_gain_pct_vs_rules"
    ]
    console_summary = {
        "benchmark_id": report["benchmark_id"],
        "config_sha256": report["config_sha256"],
        "incremental_value_relative_gain_pct_ci95": comparison[
            "incremental_value_relative_recovered_revenue_gain_pct_ci95"
        ],
        "incremental_value_seed_win_rate": comparison[
            "incremental_value_seed_win_rate"
        ],
        "incremental_value_directional_claim": comparison[
            "incremental_value_directional_claim"
        ],
        "incremental_value_gain_distribution": variability,
        "negative_incremental_value_seeds": report["negative_seeds"][
            "incremental_value"
        ],
    }
    print(json.dumps(console_summary, indent=2))
    print(f"Saved final report to {output}")
    for path in chart_paths:
        print(f"Saved chart to {path}")


if __name__ == "__main__":
    main()
