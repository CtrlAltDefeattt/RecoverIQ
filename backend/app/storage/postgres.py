from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row

from backend.app.domain.events import NormalizedPaymentEvent


class PostgresRecoveryRepository:
    """Neon-backed transactional persistence for recovery state and audits."""

    def __init__(self, database_url: str):
        if not database_url:
            raise ValueError("DATABASE_URL is required for Postgres storage")
        self.database_url = database_url

    @contextmanager
    def transaction(self) -> Iterator[Connection]:
        with psycopg.connect(
            self.database_url,
            row_factory=dict_row,
            connect_timeout=10,
        ) as connection:
            try:
                yield connection
            except Exception:
                connection.rollback()
                raise
            else:
                connection.commit()

    def close(self) -> None:
        """Connections are request-scoped, so there is nothing persistent to close."""

    def claim_event(self, event_id: str, payload: dict) -> bool:
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        with self.transaction() as connection:
            inserted = connection.execute(
                """
                INSERT INTO webhook_events(event_id, event_type, payload_json)
                VALUES (%s, %s, %s)
                ON CONFLICT (event_id) DO NOTHING
                RETURNING event_id
                """,
                (event_id, payload.get("event"), payload_json),
            ).fetchone()
            if not inserted:
                return False
            self._audit(
                connection,
                "event",
                event_id,
                "EVENT_RECEIVED",
                {"event_type": payload.get("event")},
            )
        return True

    def complete_event(self, event_id: str, status: str, result: dict) -> None:
        result_json = json.dumps(result, sort_keys=True, separators=(",", ":"))
        with self.transaction() as connection:
            connection.execute(
                """
                UPDATE webhook_events
                SET processing_status = %s, result_json = %s,
                    processed_at = CURRENT_TIMESTAMP
                WHERE event_id = %s
                """,
                (status, result_json, event_id),
            )
            self._audit(
                connection,
                "event",
                event_id,
                "EVENT_COMPLETED",
                {"status": status},
            )

    def attach_event_identity(
        self,
        event_id: str,
        event_type: str,
        payment_id: str,
    ) -> None:
        with self.transaction() as connection:
            connection.execute(
                """
                UPDATE webhook_events
                SET event_type = %s, payment_id = %s
                WHERE event_id = %s
                """,
                (event_type, payment_id, event_id),
            )

    def upsert_failed_case(
        self,
        event: NormalizedPaymentEvent,
        failure_reason: str,
    ) -> tuple[dict, bool]:
        customer_id = event.customer_email or event.customer_contact or event.payment_id
        with self.transaction() as connection:
            existing = connection.execute(
                "SELECT * FROM recovery_cases WHERE payment_id = %s FOR UPDATE",
                (event.payment_id,),
            ).fetchone()
            if existing and existing["status"] == "RECOVERED":
                self._audit(
                    connection,
                    "case",
                    event.payment_id,
                    "STALE_FAILURE_IGNORED",
                    {"event_id": event.event_id},
                )
                return dict(existing), True

            if existing:
                connection.execute(
                    """
                    UPDATE recovery_cases
                    SET amount_paise = %s, currency = %s, payment_method = %s,
                        failure_reason = %s, version = version + 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE payment_id = %s
                    """,
                    (
                        event.amount_paise,
                        event.currency,
                        event.payment_method,
                        failure_reason,
                        event.payment_id,
                    ),
                )
                audit_type = "CASE_FAILURE_REFRESHED"
            else:
                inserted = connection.execute(
                    """
                    INSERT INTO recovery_cases(
                        payment_id, case_id, customer_id, amount_paise,
                        currency, payment_method, failure_reason, status,
                        first_failed_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'AT_RISK', %s)
                    ON CONFLICT (payment_id) DO NOTHING
                    RETURNING payment_id
                    """,
                    (
                        event.payment_id,
                        f"case_{event.payment_id}",
                        customer_id,
                        event.amount_paise,
                        event.currency,
                        event.payment_method,
                        failure_reason,
                        event.created_at,
                    ),
                ).fetchone()
                if inserted:
                    audit_type = "CASE_OPENED"
                else:
                    existing = connection.execute(
                        "SELECT * FROM recovery_cases WHERE payment_id = %s FOR UPDATE",
                        (event.payment_id,),
                    ).fetchone()
                    if existing["status"] == "RECOVERED":
                        self._audit(
                            connection,
                            "case",
                            event.payment_id,
                            "STALE_FAILURE_IGNORED",
                            {"event_id": event.event_id},
                        )
                        return dict(existing), True
                    connection.execute(
                        """
                        UPDATE recovery_cases
                        SET amount_paise = %s, currency = %s, payment_method = %s,
                            failure_reason = %s, version = version + 1,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE payment_id = %s
                        """,
                        (
                            event.amount_paise,
                            event.currency,
                            event.payment_method,
                            failure_reason,
                            event.payment_id,
                        ),
                    )
                    audit_type = "CASE_FAILURE_REFRESHED"

            self._audit(
                connection,
                "case",
                event.payment_id,
                audit_type,
                {"event_id": event.event_id},
            )
            row = connection.execute(
                "SELECT * FROM recovery_cases WHERE payment_id = %s",
                (event.payment_id,),
            ).fetchone()
            return dict(row), False

    def close_recovered_case(self, event: NormalizedPaymentEvent) -> dict:
        customer_id = event.customer_email or event.customer_contact or event.payment_id
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO recovery_cases(
                    payment_id, case_id, customer_id, amount_paise, currency,
                    payment_method, status, recovered_at, recovered_amount_paise
                ) VALUES (%s, %s, %s, %s, %s, %s, 'RECOVERED', %s, %s)
                ON CONFLICT(payment_id) DO UPDATE SET
                    status = 'RECOVERED',
                    recovered_at = EXCLUDED.recovered_at,
                    recovered_amount_paise = EXCLUDED.recovered_amount_paise,
                    version = recovery_cases.version + 1,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    event.payment_id,
                    f"case_{event.payment_id}",
                    customer_id,
                    event.amount_paise,
                    event.currency,
                    event.payment_method,
                    event.created_at,
                    event.amount_paise,
                ),
            )
            connection.execute(
                """
                INSERT INTO outcomes(
                    event_id, payment_id, recovered,
                    recovered_amount_paise, observed
                ) VALUES (%s, %s, TRUE, %s, TRUE)
                """,
                (event.event_id, event.payment_id, event.amount_paise),
            )
            self._audit(
                connection,
                "case",
                event.payment_id,
                "CASE_RECOVERED",
                {"event_id": event.event_id, "amount_paise": event.amount_paise},
            )
            row = connection.execute(
                "SELECT * FROM recovery_cases WHERE payment_id = %s",
                (event.payment_id,),
            ).fetchone()
            return dict(row)

    def get_case(self, payment_id: str) -> dict | None:
        return self._one(
            "SELECT * FROM recovery_cases WHERE payment_id = %s",
            (payment_id,),
        )

    def get_event(self, event_id: str) -> dict | None:
        return self._one(
            "SELECT * FROM webhook_events WHERE event_id = %s",
            (event_id,),
        )

    def set_case_safety_state(
        self,
        payment_id: str,
        *,
        opted_out: bool | None = None,
        attempts: int | None = None,
        contacts_last_7d: int | None = None,
    ) -> None:
        updates = []
        values = []
        for column, value in (
            ("opted_out", opted_out),
            ("attempts", attempts),
            ("contacts_last_7d", contacts_last_7d),
        ):
            if value is not None:
                updates.append(f"{column} = %s")
                values.append(value)
        if not updates:
            return
        values.append(payment_id)
        with self.transaction() as connection:
            cursor = connection.execute(
                f"""
                UPDATE recovery_cases
                SET {', '.join(updates)}, version = version + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE payment_id = %s
                """,
                values,
            )
            if cursor.rowcount != 1:
                raise KeyError(payment_id)
            self._audit(
                connection,
                "case",
                payment_id,
                "SAFETY_STATE_CHANGED",
                {
                    "opted_out": opted_out,
                    "attempts": attempts,
                    "contacts_last_7d": contacts_last_7d,
                },
            )

    def record_decision(
        self,
        *,
        event_id: str,
        payment_id: str,
        mode: str,
        recommended_action: str,
        policy_decision: str,
        policy_reason: str,
        execution_status: str,
    ) -> int:
        with self.transaction() as connection:
            row = connection.execute(
                """
                INSERT INTO decisions(
                    event_id, payment_id, mode, recommended_action,
                    policy_decision, policy_reason, execution_status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    event_id,
                    payment_id,
                    mode,
                    recommended_action,
                    policy_decision,
                    policy_reason,
                    execution_status,
                ),
            ).fetchone()
            decision_id = int(row["id"])
            self._audit(
                connection,
                "case",
                payment_id,
                "DECISION_RECORDED",
                {
                    "decision_id": decision_id,
                    "action": recommended_action,
                    "policy_decision": policy_decision,
                },
            )
            return decision_id

    def record_action(
        self,
        *,
        decision_id: int,
        payment_id: str,
        idempotency_key: str,
        action: str,
        status: str,
    ) -> int:
        with self.transaction() as connection:
            row = connection.execute(
                """
                INSERT INTO actions(
                    decision_id, payment_id, idempotency_key, action, status
                ) VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (decision_id, payment_id, idempotency_key, action, status),
            ).fetchone()
            action_id = int(row["id"])
            self._audit(
                connection,
                "case",
                payment_id,
                "ACTION_RECORDED",
                {"action_id": action_id, "action": action, "status": status},
            )
            return action_id

    def update_decision_execution_status(
        self,
        decision_id: int,
        execution_status: str,
    ) -> None:
        with self.transaction() as connection:
            cursor = connection.execute(
                "UPDATE decisions SET execution_status = %s WHERE id = %s",
                (execution_status, decision_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(decision_id)

    def complete_action(
        self,
        action_id: int,
        *,
        status: str,
        external_action_id: str | None = None,
        external_action_url: str | None = None,
        increment_attempt: bool = False,
        increment_contact: bool = False,
    ) -> None:
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT payment_id FROM actions WHERE id = %s FOR UPDATE",
                (action_id,),
            ).fetchone()
            if not row:
                raise KeyError(action_id)
            connection.execute(
                """
                UPDATE actions
                SET status = %s, external_action_id = %s, external_action_url = %s,
                    completed_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (status, external_action_id, external_action_url, action_id),
            )
            if increment_attempt or increment_contact:
                connection.execute(
                    """
                    UPDATE recovery_cases
                    SET attempts = attempts + %s,
                        contacts_last_7d = contacts_last_7d + %s,
                        version = version + 1, updated_at = CURRENT_TIMESTAMP
                    WHERE payment_id = %s AND status = 'AT_RISK'
                    """,
                    (int(increment_attempt), int(increment_contact), row["payment_id"]),
                )
            self._audit(
                connection,
                "case",
                row["payment_id"],
                "ACTION_COMPLETED",
                {"action_id": action_id, "status": status},
            )

    def list_audit(self, aggregate_type: str, aggregate_id: str) -> list[dict]:
        return self._all(
            """
            SELECT * FROM audit_log
            WHERE aggregate_type = %s AND aggregate_id = %s
            ORDER BY id
            """,
            (aggregate_type, aggregate_id),
        )

    def list_case_decisions(self, payment_id: str) -> list[dict]:
        return self._all(
            "SELECT * FROM decisions WHERE payment_id = %s ORDER BY id",
            (payment_id,),
        )

    def list_case_actions(self, payment_id: str) -> list[dict]:
        return self._all(
            "SELECT * FROM actions WHERE payment_id = %s ORDER BY id",
            (payment_id,),
        )

    def counts(self) -> dict[str, int]:
        tables = (
            "webhook_events",
            "recovery_cases",
            "decisions",
            "actions",
            "outcomes",
            "audit_log",
        )
        with self.transaction() as connection:
            return {
                table: int(
                    connection.execute(
                        f"SELECT COUNT(*) AS count FROM {table}"
                    ).fetchone()["count"]
                )
                for table in tables
            }

    def clear_all(self) -> None:
        with self.transaction() as connection:
            for table in (
                "outcomes",
                "actions",
                "decisions",
                "recovery_cases",
                "webhook_events",
                "audit_log",
            ):
                connection.execute(f"DELETE FROM {table}")

    def ping(self) -> bool:
        with self.transaction() as connection:
            row = connection.execute("SELECT 1 AS healthy").fetchone()
            return row["healthy"] == 1

    def _one(self, query: str, parameters: tuple) -> dict | None:
        with self.transaction() as connection:
            row = connection.execute(query, parameters).fetchone()
            return dict(row) if row else None

    def _all(self, query: str, parameters: tuple) -> list[dict]:
        with self.transaction() as connection:
            rows = connection.execute(query, parameters).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def _audit(
        connection: Connection,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        details: dict,
    ) -> None:
        connection.execute(
            """
            INSERT INTO audit_log(
                aggregate_type, aggregate_id, event_type, details_json
            ) VALUES (%s, %s, %s, %s)
            """,
            (
                aggregate_type,
                aggregate_id,
                event_type,
                json.dumps(details, sort_keys=True, separators=(",", ":")),
            ),
        )
