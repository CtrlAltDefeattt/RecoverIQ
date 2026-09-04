from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from backend.app.services.razorpay_integration import RazorpayIntegrationService
from backend.app.storage.sqlite import SQLiteRecoveryRepository

PAYMENT_METHODS = ("upi", "card", "netbanking", "wallet")
FAILURE_REASONS = (
    "insufficient_funds",
    "authentication_failed",
    "gateway_error",
    "incorrect_otp",
)


class NoNetworkAdapter:
    async def create_payment_link(self, **_kwargs) -> dict:
        raise AssertionError("The shadow-mode demo seed must never call Razorpay")


def payment_payload(
    event_type: str,
    payment_id: str,
    *,
    amount_paise: int,
    method: str,
    failure_reason: str,
    created_at: int,
) -> dict:
    return {
        "entity": "event",
        "event": event_type,
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "amount": amount_paise,
                    "currency": "INR",
                    "status": (
                        "failed" if event_type == "payment.failed" else "captured"
                    ),
                    "order_id": f"order_{payment_id}",
                    "method": method,
                    "email": f"{payment_id}@example.com",
                    "contact": "+919000000000",
                    "error_reason": (
                        failure_reason if event_type == "payment.failed" else None
                    ),
                    "error_source": (
                        "bank" if event_type == "payment.failed" else None
                    ),
                    "created_at": created_at,
                }
            }
        },
    }


async def seed_demo_data(
    database_path: str,
    *,
    cases: int = 12,
    seed: int = 42,
    reset: bool = True,
) -> dict:
    if cases < 1:
        raise ValueError("cases must be at least 1")

    repository = SQLiteRecoveryRepository(database_path)
    if reset:
        repository.clear_all()

    service = RazorpayIntegrationService(repository=repository)
    adapter = NoNetworkAdapter()
    recovered_ids: list[str] = []
    recovered_amount_paise = 0
    base_created_at = 1_780_000_000 + seed * 10_000

    for index in range(cases):
        payment_id = f"pay_demo_{seed}_{index:04d}"
        amount_paise = 100_000 + ((seed * 7_919 + index * 104_729) % 1_400_000)
        method = PAYMENT_METHODS[(seed + index) % len(PAYMENT_METHODS)]
        failure_reason = FAILURE_REASONS[(seed * 3 + index) % len(FAILURE_REASONS)]
        created_at = base_created_at + index * 3_600

        await service.process(
            f"evt_demo_failed_{seed}_{index:04d}",
            payment_payload(
                "payment.failed",
                payment_id,
                amount_paise=amount_paise,
                method=method,
                failure_reason=failure_reason,
                created_at=created_at,
            ),
            mode="shadow",
            execute_razorpay_actions=False,
            adapter=adapter,
        )

        if (seed + index) % 3 == 0:
            await service.process(
                f"evt_demo_captured_{seed}_{index:04d}",
                payment_payload(
                    "payment.captured",
                    payment_id,
                    amount_paise=amount_paise,
                    method=method,
                    failure_reason=failure_reason,
                    created_at=created_at + 86_400,
                ),
                mode="shadow",
                execute_razorpay_actions=False,
                adapter=adapter,
            )
            recovered_ids.append(payment_id)
            recovered_amount_paise += amount_paise

    summary = {
        "schema_version": 1,
        "synthetic": True,
        "mode": "shadow",
        "seed": seed,
        "requested_cases": cases,
        "recovered_cases": len(recovered_ids),
        "recovered_amount_paise": recovered_amount_paise,
        "ledger_counts": repository.counts(),
        "network_calls": 0,
    }
    repository.close()
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a deterministic, synthetic RecoverIQ demo ledger."
    )
    parser.add_argument(
        "--database",
        default="data/recoveriq-demo.sqlite3",
        help="SQLite database path (default: data/recoveriq-demo.sqlite3)",
    )
    parser.add_argument("--cases", type=int, default=12)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output",
        default="outputs/day9_demo_seed_summary.json",
        help="Deterministic JSON summary path",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Keep existing rows instead of resetting the demo ledger first",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = asyncio.run(
        seed_demo_data(
            args.database,
            cases=args.cases,
            seed=args.seed,
            reset=not args.append,
        )
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
