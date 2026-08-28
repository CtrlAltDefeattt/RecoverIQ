from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from backend.app.domain.events import NormalizedPaymentEvent


SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_meta (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS webhook_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT,
    payment_id TEXT,
    payload_json TEXT NOT NULL,
    processing_status TEXT NOT NULL DEFAULT 'RECEIVED',
    result_json TEXT,
    received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at TEXT
);

CREATE TABLE IF NOT EXISTS recovery_cases (
    payment_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL UNIQUE,
    customer_id TEXT NOT NULL,
    amount_paise INTEGER NOT NULL CHECK (amount_paise > 0),
    currency TEXT NOT NULL,
    payment_method TEXT NOT NULL,
    failure_reason TEXT,
    status TEXT NOT NULL CHECK (
        status IN ('AT_RISK', 'RECOVERED', 'STOPPED', 'ESCALATED')
    ),
    opted_out INTEGER NOT NULL DEFAULT 0 CHECK (opted_out IN (0, 1)),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    contacts_last_7d INTEGER NOT NULL DEFAULT 0 CHECK (contacts_last_7d >= 0),
    first_failed_at INTEGER,
    recovered_at INTEGER,
    recovered_amount_paise INTEGER NOT NULL DEFAULT 0,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE REFERENCES webhook_events(event_id),
    payment_id TEXT NOT NULL REFERENCES recovery_cases(payment_id),
    mode TEXT NOT NULL,
    recommended_action TEXT NOT NULL,
    policy_decision TEXT NOT NULL,
    policy_reason TEXT NOT NULL,
    execution_status TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id INTEGER NOT NULL UNIQUE REFERENCES decisions(id),
    payment_id TEXT NOT NULL REFERENCES recovery_cases(payment_id),
    idempotency_key TEXT NOT NULL UNIQUE,
    action TEXT NOT NULL,
    status TEXT NOT NULL,
    external_action_id TEXT,
    external_action_url TEXT,
    requested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE REFERENCES webhook_events(event_id),
    payment_id TEXT NOT NULL REFERENCES recovery_cases(payment_id),
    action_id INTEGER REFERENCES actions(id),
    recovered INTEGER NOT NULL CHECK (recovered IN (0, 1)),
    recovered_amount_paise INTEGER NOT NULL DEFAULT 0,
    observed INTEGER NOT NULL CHECK (observed IN (0, 1)),
    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    aggregate_type TEXT NOT NULL,
    aggregate_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    details_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_events_payment ON webhook_events(payment_id);
CREATE INDEX IF NOT EXISTS idx_decisions_payment ON decisions(payment_id);
CREATE INDEX IF NOT EXISTS idx_actions_payment ON actions(payment_id);
CREATE INDEX IF NOT EXISTS idx_audit_aggregate
    ON audit_log(aggregate_type, aggregate_id, id);
"""


class SQLiteRecoveryRepository:
    """Transactional persistence for webhook idempotency and recovery audits."""

    def __init__(self, database_path: str):
        self.database_path = database_path
        if database_path != ":memory:":
            Path(database_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(
            database_path,
            check_same_thread=False,
            isolation_level=None,
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA busy_timeout = 5000")
        if database_path != ":memory:":
            self._connection.execute("PRAGMA journal_mode = WAL")
        self._lock = threading.RLock()
        with self._lock:
            self._connection.executescript(SCHEMA)
            self._connection.execute(
                "INSERT OR IGNORE INTO schema_meta(version) VALUES (1)"
            )

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                yield self._connection
            except Exception:
                self._connection.rollback()
                raise
            else:
                self._connection.commit()

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def claim_event(self, event_id: str, payload: dict) -> bool:
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        try:
            with self.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO webhook_events(event_id, event_type, payload_json)
                    VALUES (?, ?, ?)
                    """,
                    (event_id, payload.get("event"), payload_json),
                )
                self._audit(
                    connection,
                    "event",
                    event_id,
                    "EVENT_RECEIVED",
                    {"event_type": payload.get("event")},
                )
        except sqlite3.IntegrityError:
            return False
        return True

    def complete_event(self, event_id: str, status: str, result: dict) -> None:
        result_json = json.dumps(result, sort_keys=True, separators=(",", ":"))
        with self.transaction() as connection:
            connection.execute(
                """
                UPDATE webhook_events
                SET processing_status = ?, result_json = ?,
                    processed_at = CURRENT_TIMESTAMP
                WHERE event_id = ?
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
                SET event_type = ?, payment_id = ?
                WHERE event_id = ?
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
                "SELECT * FROM recovery_cases WHERE payment_id = ?",
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
                    SET amount_paise = ?, currency = ?, payment_method = ?,
                        failure_reason = ?, version = version + 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE payment_id = ?
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
                connection.execute(
                    """
                    INSERT INTO recovery_cases(
                        payment_id, case_id, customer_id, amount_paise,
                        currency, payment_method, failure_reason, status,
                        first_failed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'AT_RISK', ?)
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
                )
                audit_type = "CASE_OPENED"

            self._audit(
                connection,
                "case",
                event.payment_id,
                audit_type,
                {"event_id": event.event_id},
            )
            row = connection.execute(
                "SELECT * FROM recovery_cases WHERE payment_id = ?",
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
                ) VALUES (?, ?, ?, ?, ?, ?, 'RECOVERED', ?, ?)
                ON CONFLICT(payment_id) DO UPDATE SET
                    status = 'RECOVERED',
                    recovered_at = excluded.recovered_at,
                    recovered_amount_paise = excluded.recovered_amount_paise,
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
                ) VALUES (?, ?, 1, ?, 1)
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
                "SELECT * FROM recovery_cases WHERE payment_id = ?",
                (event.payment_id,),
            ).fetchone()
            return dict(row)

    def get_case(self, payment_id: str) -> dict | None:
        return self._one(
            "SELECT * FROM recovery_cases WHERE payment_id = ?",
            (payment_id,),
        )

    def get_event(self, event_id: str) -> dict | None:
        return self._one(
            "SELECT * FROM webhook_events WHERE event_id = ?",
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
            ("opted_out", None if opted_out is None else int(opted_out)),
            ("attempts", attempts),
            ("contacts_last_7d", contacts_last_7d),
        ):
            if value is not None:
                updates.append(f"{column} = ?")
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
                WHERE payment_id = ?
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
            cursor = connection.execute(
                """
                INSERT INTO decisions(
                    event_id, payment_id, mode, recommended_action,
                    policy_decision, policy_reason, execution_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
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
            )
            decision_id = int(cursor.lastrowid)
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
            cursor = connection.execute(
                """
                INSERT INTO actions(
                    decision_id, payment_id, idempotency_key, action, status
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (decision_id, payment_id, idempotency_key, action, status),
            )
            action_id = int(cursor.lastrowid)
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
                "UPDATE decisions SET execution_status = ? WHERE id = ?",
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
                "SELECT payment_id FROM actions WHERE id = ?",
                (action_id,),
            ).fetchone()
            if not row:
                raise KeyError(action_id)
            connection.execute(
                """
                UPDATE actions
                SET status = ?, external_action_id = ?, external_action_url = ?,
                    completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, external_action_id, external_action_url, action_id),
            )
            if increment_attempt or increment_contact:
                connection.execute(
                    """
                    UPDATE recovery_cases
                    SET attempts = attempts + ?, contacts_last_7d = contacts_last_7d + ?,
                        version = version + 1, updated_at = CURRENT_TIMESTAMP
                    WHERE payment_id = ? AND status = 'AT_RISK'
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
            WHERE aggregate_type = ? AND aggregate_id = ?
            ORDER BY id
            """,
            (aggregate_type, aggregate_id),
        )

    def list_case_decisions(self, payment_id: str) -> list[dict]:
        return self._all(
            "SELECT * FROM decisions WHERE payment_id = ? ORDER BY id",
            (payment_id,),
        )

    def list_case_actions(self, payment_id: str) -> list[dict]:
        return self._all(
            "SELECT * FROM actions WHERE payment_id = ? ORDER BY id",
            (payment_id,),
        )

    def counts(self) -> dict[str, int]:
        with self._lock:
            return {
                table: int(
                    self._connection.execute(
                        f"SELECT COUNT(*) FROM {table}"
                    ).fetchone()[0]
                )
                for table in (
                    "webhook_events",
                    "recovery_cases",
                    "decisions",
                    "actions",
                    "outcomes",
                    "audit_log",
                )
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

    def _one(self, query: str, parameters: tuple) -> dict | None:
        with self._lock:
            row = self._connection.execute(query, parameters).fetchone()
            return dict(row) if row else None

    def _all(self, query: str, parameters: tuple) -> list[dict]:
        with self._lock:
            rows = self._connection.execute(query, parameters).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def _audit(
        connection: sqlite3.Connection,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        details: dict,
    ) -> None:
        connection.execute(
            """
            INSERT INTO audit_log(
                aggregate_type, aggregate_id, event_type, details_json
            ) VALUES (?, ?, ?, ?)
            """,
            (
                aggregate_type,
                aggregate_id,
                event_type,
                json.dumps(details, sort_keys=True, separators=(",", ":")),
            ),
        )
