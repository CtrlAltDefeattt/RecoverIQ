from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.app.simulator.benchmark import multiseed_benchmark


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=int, default=10000)
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--output", default="outputs/multiseed_results.json")
    args = parser.parse_args()

    summary = multiseed_benchmark(events=args.events, seeds=args.seeds)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    console_summary = {key: value for key, value in summary.items() if key != "runs"}
    print(json.dumps(console_summary, indent=2))
    print(f"Saved full results to {out}")


if __name__ == "__main__":
    main()
