from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from backend.app.simulator.benchmark import benchmark


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=int, default=10000)
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--output", default="outputs/multiseed_results.json")
    args = parser.parse_args()

    runs = []
    for seed in range(args.seeds):
        result = benchmark(events=args.events, seed=seed)
        runs.append({"seed": seed, **result})

    relative_gains = [
        r["comparison"]["linucb_relative_gain_pct_vs_rules"] for r in runs
    ]
    additional_simulated_revenue = [
        r["comparison"]["linucb_additional_simulated_rupees_vs_rules"]
        for r in runs
    ]

    summary = {
        "events_per_seed": args.events,
        "seed_count": args.seeds,
        "mean_relative_gain_pct_vs_rules": round(
            statistics.mean(relative_gains), 3
        ),
        "std_relative_gain_pct_vs_rules": round(
            statistics.pstdev(relative_gains), 3
        ),
        "mean_additional_simulated_rupees_vs_rules": round(
            statistics.mean(additional_simulated_revenue), 2
        ),
        "runs": runs,
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "runs"}, indent=2))
    print(f"Saved full results to {out}")


if __name__ == "__main__":
    main()
