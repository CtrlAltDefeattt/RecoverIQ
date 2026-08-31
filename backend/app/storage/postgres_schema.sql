CREATE TABLE IF NOT EXISTS schema_meta (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS webhook_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT,
    payment_id TEXT,
    payload_json TEXT NOT NULL,
    processing_status TEXT NOT NULL DEFAULT 'RECEIVED',
    result_json TEXT,
    received_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS recovery_cases (
    payment_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL UNIQUE,
    customer_id TEXT NOT NULL,
    amount_paise BIGINT NOT NULL CHECK (amount_paise > 0),
    currency TEXT NOT NULL,
    payment_method TEXT NOT NULL,
    failure_reason TEXT,
    status TEXT NOT NULL CHECK (
        status IN ('AT_RISK', 'RECOVERED', 'STOPPED', 'ESCALATED')
    ),
    opted_out BOOLEAN NOT NULL DEFAULT FALSE,
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    contacts_last_7d INTEGER NOT NULL DEFAULT 0 CHECK (contacts_last_7d >= 0),
    first_failed_at BIGINT,
    recovered_at BIGINT,
    recovered_amount_paise BIGINT NOT NULL DEFAULT 0,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS decisions (
    id BIGSERIAL PRIMARY KEY,
    event_id TEXT NOT NULL UNIQUE REFERENCES webhook_events(event_id),
    payment_id TEXT NOT NULL REFERENCES recovery_cases(payment_id),
    mode TEXT NOT NULL,
    recommended_action TEXT NOT NULL,
    policy_decision TEXT NOT NULL,
    policy_reason TEXT NOT NULL,
    execution_status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS actions (
    id BIGSERIAL PRIMARY KEY,
    decision_id BIGINT NOT NULL UNIQUE REFERENCES decisions(id),
    payment_id TEXT NOT NULL REFERENCES recovery_cases(payment_id),
    idempotency_key TEXT NOT NULL UNIQUE,
    action TEXT NOT NULL,
    status TEXT NOT NULL,
    external_action_id TEXT,
    external_action_url TEXT,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS outcomes (
    id BIGSERIAL PRIMARY KEY,
    event_id TEXT NOT NULL UNIQUE REFERENCES webhook_events(event_id),
    payment_id TEXT NOT NULL REFERENCES recovery_cases(payment_id),
    action_id BIGINT REFERENCES actions(id),
    recovered BOOLEAN NOT NULL,
    recovered_amount_paise BIGINT NOT NULL DEFAULT 0,
    observed BOOLEAN NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    aggregate_type TEXT NOT NULL,
    aggregate_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    details_json TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_events_payment ON webhook_events(payment_id);
CREATE INDEX IF NOT EXISTS idx_decisions_payment ON decisions(payment_id);
CREATE INDEX IF NOT EXISTS idx_actions_payment ON actions(payment_id);
CREATE INDEX IF NOT EXISTS idx_audit_aggregate
    ON audit_log(aggregate_type, aggregate_id, id);

INSERT INTO schema_meta(version) VALUES (1)
ON CONFLICT (version) DO NOTHING;
