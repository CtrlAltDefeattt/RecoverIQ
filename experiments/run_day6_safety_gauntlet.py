from __future__ import annotations

import argparse
import asyncio
import json
import tempfile
from pathlib import Path

from backend.app.services.razorpay_integration import RazorpayIntegrationService
from backend.app.storage.sqlite import SQLiteRecoveryRepository


class RecordingAdapter:
    def __init__(self):
        self.calls = []

    async def create_payment_link(self, **kwargs) -> dict:
        self.calls.append(kwargs)
        sequence = len(self.calls)
        return {
            "id": f"plink_gauntlet_{sequence}",
            "short_url": f"https://rzp.io/i/gauntlet{sequence}",
        }


def payment_payload(
    event_type: str,
    payment_id: str,
    *,
    amount_paise: int = 499_900,
    created_at: int = 1_780_000_000,
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
                    "method": "upi",
                    "email": f"{payment_id}@example.com",
                    "contact": "+919999999999",
                    "error_reason": (
                        "authentication_failed"
                        if event_type == "payment.failed"
                        else None
                    ),
                    "error_source": (
                        "bank" if event_type == "payment.failed" else None
                    ),
                    "created_at": created_at,
                }
            }
        },
    }


async def _process(
    service: RazorpayIntegrationService,
    adapter: RecordingAdapter,
    event_id: str,
    payload: dict,
    *,
    mode: str = "autonomous",
    execute: bool = True,
) -> dict:
    return await service.process(
        event_id,
        payload,
        mode=mode,
        execute_razorpay_actions=execute,
        adapter=adapter,
    )


async def _run(database_path: str) -> dict:
    repository = SQLiteRecoveryRepository(database_path)
    service = RazorpayIntegrationService(repository=repository)
    adapter = RecordingAdapter()
    scenarios = {}

    duplicate_payload = payment_payload("payment.failed", "pay_duplicate")
    duplicate_first = await _process(
        service,
        adapter,
        "evt_duplicate",
        duplicate_payload,
        mode="shadow",
        execute=False,
    )
    duplicate_second = await _process(
        service,
        adapter,
        "evt_duplicate",
        duplicate_payload,
        mode="shadow",
        execute=False,
    )
    scenarios["duplicate_event"] = {
        "passed": (
            duplicate_first["status"] == "decision_recorded"
            and duplicate_second["status"] == "duplicate_ignored"
            and len(repository.list_case_decisions("pay_duplicate")) == 1
        ),
        "result": duplicate_second["status"],
    }

    opt_out_payload = payment_payload("payment.failed", "pay_opted_out")
    await _process(
        service,
        adapter,
        "evt_optout_open",
        opt_out_payload,
        mode="shadow",
        execute=False,
    )
    repository.set_case_safety_state("pay_opted_out", opted_out=True)
    calls_before = len(adapter.calls)
    opted_out = await _process(
        service,
        adapter,
        "evt_optout_retry",
        opt_out_payload,
    )
    scenarios["customer_opt_out"] = {
        "passed": (
            opted_out["recommended_action"] == "NO_ACTION"
            and opted_out["blocked_action_reasons"].get("PAYMENT_LINK")
            == "CUSTOMER_OPT_OUT"
            and len(adapter.calls) == calls_before
        ),
        "result": opted_out["execution_status"],
    }

    high_value = await _process(
        service,
        adapter,
        "evt_high_value",
        payment_payload(
            "payment.failed",
            "pay_high_value",
            amount_paise=2_500_000,
        ),
    )
    scenarios["high_value_approval"] = {
        "passed": (
            high_value["policy_decision"] == "REQUIRE_APPROVAL"
            and high_value["execution_status"] == "awaiting_human_approval"
        ),
        "result": high_value["execution_status"],
    }

    attempt_payload = payment_payload("payment.failed", "pay_attempt_limit")
    await _process(
        service,
        adapter,
        "evt_attempt_open",
        attempt_payload,
        mode="shadow",
        execute=False,
    )
    repository.set_case_safety_state("pay_attempt_limit", attempts=3)
    calls_before = len(adapter.calls)
    exhausted = await _process(
        service,
        adapter,
        "evt_attempt_retry",
        attempt_payload,
    )
    scenarios["attempt_limit"] = {
        "passed": (
            exhausted["recommended_action"] == "NO_ACTION"
            and exhausted["blocked_action_reasons"].get("PAYMENT_LINK")
            == "MAX_ATTEMPTS_REACHED"
            and len(adapter.calls) == calls_before
        ),
        "result": exhausted["execution_status"],
    }

    captured = await _process(
        service,
        adapter,
        "evt_capture_first",
        payment_payload("payment.captured", "pay_already_paid"),
    )
    stale = await _process(
        service,
        adapter,
        "evt_failure_late",
        payment_payload("payment.failed", "pay_already_paid"),
    )
    scenarios["already_paid_terminal"] = {
        "passed": (
            captured["status"] == "case_closed"
            and stale["status"] == "stale_failure_ignored"
            and repository.get_case("pay_already_paid")["status"] == "RECOVERED"
            and not repository.list_case_decisions("pay_already_paid")
        ),
        "result": stale["status"],
    }

    execute_payload = payment_payload("payment.failed", "pay_exactly_once")
    calls_before = len(adapter.calls)
    executed = await _process(
        service,
        adapter,
        "evt_exactly_once",
        execute_payload,
    )
    repeated = await _process(
        service,
        adapter,
        "evt_exactly_once",
        execute_payload,
    )
    exact_case = repository.get_case("pay_exactly_once")
    exact_actions = repository.list_case_actions("pay_exactly_once")
    scenarios["exactly_once_execution"] = {
        "passed": (
            executed["execution_status"] == "executed"
            and repeated["status"] == "duplicate_ignored"
            and len(adapter.calls) == calls_before + 1
            and len(exact_actions) == 1
            and exact_actions[0]["status"] == "executed"
            and exact_case["attempts"] == 1
            and exact_case["contacts_last_7d"] == 1
        ),
        "result": repeated["status"],
    }

    audit = repository.list_audit("case", "pay_exactly_once")
    audit_types = {entry["event_type"] for entry in audit}
    scenarios["audit_completeness"] = {
        "passed": {
            "CASE_OPENED",
            "DECISION_RECORDED",
            "ACTION_RECORDED",
            "ACTION_COMPLETED",
        }.issubset(audit_types),
        "result": sorted(audit_types),
    }

    result = {
        "scenario_count": len(scenarios),
        "passed_count": sum(item["passed"] for item in scenarios.values()),
        "all_passed": all(item["passed"] for item in scenarios.values()),
        "scenarios": scenarios,
        "persistence_counts": repository.counts(),
        "real_network_calls": 0,
        "fake_adapter_calls": len(adapter.calls),
    }
    repository.close()
    return result


def run_gauntlet(database_path: str | None = None) -> dict:
    if database_path:
        return asyncio.run(_run(database_path))
    with tempfile.TemporaryDirectory(prefix="recoveriq_day6_") as directory:
        return asyncio.run(_run(str(Path(directory) / "gauntlet.sqlite3")))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="outputs/day6_safety_gauntlet.json",
    )
    args = parser.parse_args()
    report = run_gauntlet()
    if not report["all_passed"]:
        raise SystemExit("Safety Gauntlet failed")
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Saved full results to {destination}")


if __name__ == "__main__":
    main()
