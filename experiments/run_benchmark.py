from __future__ import annotations

import argparse
import json

from backend.app.simulator.benchmark import benchmark


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    result = benchmark(events=args.events, seed=args.seed)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
