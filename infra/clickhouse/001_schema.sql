CREATE TABLE IF NOT EXISTS production_events (
    occurred_at DateTime DEFAULT now(),
    session_id String,
    user_id String,
    event_type LowCardinality(String),
    media_id Nullable(String),
    proposed_value Nullable(String),
    accepted_value Nullable(String),
    agent_confidence Float32,
    render_id Nullable(String)
) ENGINE = MergeTree
ORDER BY (user_id, session_id, occurred_at);

CREATE TABLE IF NOT EXISTS creative_preferences (
    occurred_at DateTime DEFAULT now(),
    user_id String,
    occasion LowCardinality(String),
    category LowCardinality(String),
    value String,
    decision LowCardinality(String)
) ENGINE = MergeTree
ORDER BY (user_id, occasion, category, occurred_at);

CREATE TABLE IF NOT EXISTS render_outcomes (
    occurred_at DateTime DEFAULT now(),
    render_id String,
    session_id String,
    output_state LowCardinality(String),
    failed_stage Nullable(String),
    retry_count UInt8
) ENGINE = MergeTree
ORDER BY (session_id, occurred_at);
