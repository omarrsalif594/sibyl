-- Production schema for LLM orchestration state store (DuckDB)
-- Version: 3 - Session Rotation Support
--
-- Changelog from v2:
-- - Added sessions table for automatic context rotation
-- - Added session_rotations table for rotation event tracking
-- - Added session_token_usage table for granular token accounting
-- - Added active_generation column for atomic session swaps
-- - Enhanced boot integrity checks for crash recovery
-- - Added ENUMs and refined indices for concurrency safety

-- ============================================================================
-- Schema Version Tracking
-- ============================================================================

CREATE TABLE IF NOT EXISTS schema_version (
    version INT PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT NOT NULL
);

-- Insert v3 marker (will be added by migration)
-- INSERT OR IGNORE INTO schema_version (version, description)
-- VALUES (3, 'Session rotation support with concurrency controls');


-- ============================================================================
-- Conversations (Top-Level Tracking)
-- ============================================================================

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    workflow_type TEXT NOT NULL,

    -- Timestamps
    started_at TIMESTAMP NOT NULL,
    finished_at TIMESTAMP,

    -- Status
    status TEXT NOT NULL
        CHECK(status IN ('running', 'completed', 'failed', 'cancelled', 'crashed')),

    -- Budget tracking
    token_budget INT NOT NULL,
    token_spent INT DEFAULT 0,
    cost_usd FLOAT DEFAULT 0.0,

    -- Context versioning (deterministic replay)
    context_hash TEXT NOT NULL,
    config_version TEXT NOT NULL,

    -- Metadata
    created_by TEXT,
    tags JSON
);

CREATE INDEX IF NOT EXISTS idx_conv_status ON conversations(status, started_at);
CREATE INDEX IF NOT EXISTS idx_conv_workflow ON conversations(workflow_type);


-- ============================================================================
-- Sessions (Automatic Context Rotation)
-- ============================================================================

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id),
    parent_session_id TEXT REFERENCES sessions(id),  -- Links to previous session after rotation
    session_number INT NOT NULL,  -- Sequential number within conversation (1, 2, 3...)

    -- Concurrency control
    active_generation INT NOT NULL DEFAULT 1,  -- Monotonic counter, incremented on swap
    rotation_in_progress BOOLEAN DEFAULT FALSE,  -- Flag to prevent concurrent rotations

    -- Budget tracking
    tokens_budget INT NOT NULL,  -- Max tokens for this session (from model context window)
    tokens_spent INT DEFAULT 0,  -- Cumulative tokens used in this session
    token_utilization_pct FLOAT DEFAULT 0.0,  -- tokens_spent / tokens_budget * 100

    -- Threshold configuration (captured at session creation)
    summarize_threshold_pct FLOAT NOT NULL,  -- Trigger background summarization (default 60)
    rotate_threshold_pct FLOAT NOT NULL,     -- Trigger rotation (default 70)

    -- Context preservation
    context_summary_ref TEXT,  -- SHA256 to blob (compressed summary from previous session)
    preserved_state JSON,      -- Critical state preserved across rotation
                               -- Example: {"model_name": "core__example__resource_facts_a", "phase": "fix", "attempt": 2}

    -- Status lifecycle
    status TEXT NOT NULL
        CHECK(status IN ('active', 'summarizing', 'rotating', 'completed', 'failed', 'abandoned'))
        DEFAULT 'active',

    -- Lifecycle timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    summarization_started_at TIMESTAMP,  -- When 60% threshold triggered
    rotation_started_at TIMESTAMP,       -- When 70% threshold triggered
    completed_at TIMESTAMP,              -- When session rotation completed or workflow ended

    -- Metadata
    model_name TEXT,  -- LLM model for this session (e.g., "claude-sonnet-4-5")
    agent_type TEXT   -- Agent type if session-specific (e.g., "FastThinker", "DeepThinker")
);

-- Indices for session queries
CREATE INDEX IF NOT EXISTS idx_session_conv ON sessions(conversation_id, session_number);
CREATE INDEX IF NOT EXISTS idx_session_status ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_session_parent ON sessions(parent_session_id);
CREATE INDEX IF NOT EXISTS idx_session_active_gen ON sessions(id, active_generation);

-- Partial index for active sessions (most frequently queried)
CREATE INDEX IF NOT EXISTS idx_session_active ON sessions(id, conversation_id)
    WHERE status = 'active';


-- ============================================================================
-- Session Rotations (Rotation Event Tracking)
-- ============================================================================

CREATE TABLE IF NOT EXISTS session_rotations (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id),

    -- Session handoff
    from_session_id TEXT NOT NULL REFERENCES sessions(id),
    to_session_id TEXT NOT NULL REFERENCES sessions(id),

    -- Rotation trigger
    trigger TEXT NOT NULL
        CHECK(trigger IN ('token_threshold', 'manual', 'error', 'timeout', 'forced')),

    tokens_before_rotation INT NOT NULL,  -- Token count that triggered rotation
    tokens_threshold INT NOT NULL,        -- Threshold that was exceeded
    utilization_pct FLOAT NOT NULL,       -- (tokens_before / budget) * 100

    -- Summarization metadata
    summarization_used BOOLEAN DEFAULT TRUE,
    summarization_strategy TEXT
        CHECK(summarization_strategy IN ('llm_compress', 'delta_compress', 'full_copy', 'restart')),
    context_summary_ref TEXT,  -- SHA256 to blob (summary used for new session)
    compression_ratio FLOAT,   -- original_tokens / summary_tokens (e.g., 10.0 means 10x compression)

    -- Agent continuity
    agent_type_before TEXT NOT NULL,
    agent_type_after TEXT NOT NULL,
    model_before TEXT,  -- Model used in old session
    model_after TEXT,   -- Model used in new session (may differ if degradation occurred)

    -- Timing and performance
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    summarization_completed_at TIMESTAMP,
    rotation_completed_at TIMESTAMP,
    summarization_latency_ms INT,  -- Time to generate summary
    handoff_duration_ms INT,       -- Total time for rotation
    blocking_duration_ms INT,      -- Time tools were blocked during rotation

    -- Preserved context metadata
    preserved_context_keys JSON,  -- List of keys preserved (e.g., ["model_name", "phase", "attempt"])
    context_size_before_bytes INT,
    context_size_after_bytes INT,

    -- Failure handling
    failure_reason TEXT,           -- Non-null if rotation failed
    fallback_used BOOLEAN DEFAULT FALSE,  -- True if deterministic fallback used (no LLM)
    retry_count INT DEFAULT 0
);

-- Indices for rotation analytics
CREATE INDEX IF NOT EXISTS idx_rotation_conv ON session_rotations(conversation_id, started_at);
CREATE INDEX IF NOT EXISTS idx_rotation_from_session ON session_rotations(from_session_id);
CREATE INDEX IF NOT EXISTS idx_rotation_trigger ON session_rotations(trigger, started_at);
CREATE INDEX IF NOT EXISTS idx_rotation_performance ON session_rotations(handoff_duration_ms);


-- ============================================================================
-- Session Token Usage (Granular Token Tracking)
-- ============================================================================

CREATE TABLE IF NOT EXISTS session_token_usage (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id),

    -- Tool call identification
    tool_name TEXT NOT NULL,
    call_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    turn_id INT NOT NULL,  -- Sequential turn number within session

    -- Token accounting
    tokens_in INT NOT NULL,     -- Request tokens (prompt + context)
    tokens_out INT NOT NULL,    -- Response tokens
    tokens_total INT NOT NULL,  -- tokens_in + tokens_out

    -- Cumulative tracking
    cumulative_tokens INT NOT NULL,  -- Running total for this session
    utilization_pct FLOAT NOT NULL,  -- (cumulative / budget) * 100

    -- Threshold proximity (for observability)
    distance_to_summarize_pct FLOAT,  -- % points until 60% threshold
    distance_to_rotate_pct FLOAT,     -- % points until 70% threshold

    -- Context
    correlation_id TEXT,  -- Distributed tracing
    span_id TEXT,

    -- Generation binding (operation boundary contract)
    active_generation INT NOT NULL,  -- Generation at entry time (immutable for this call)
    generation_at_completion INT     -- Generation when call completed (may differ if rotation occurred)
);

-- Indices for token usage queries
CREATE INDEX IF NOT EXISTS idx_token_usage_session ON session_token_usage(session_id, turn_id);
CREATE INDEX IF NOT EXISTS idx_token_usage_time ON session_token_usage(call_timestamp);
CREATE INDEX IF NOT EXISTS idx_token_usage_tool ON session_token_usage(tool_name, call_timestamp);
CREATE INDEX IF NOT EXISTS idx_token_usage_correlation ON session_token_usage(correlation_id);

-- Partial index for threshold monitoring (hot queries)
CREATE INDEX IF NOT EXISTS idx_token_usage_threshold ON session_token_usage(session_id, utilization_pct)
    WHERE utilization_pct >= 50.0;  -- Only track approaches to threshold


-- ============================================================================
-- Phase Checkpoints (Phase Boundaries)
-- ============================================================================

CREATE TABLE IF NOT EXISTS phase_checkpoints (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id),
    phase TEXT NOT NULL,
    phase_number INT NOT NULL,

    -- Status
    status TEXT NOT NULL
        CHECK(status IN ('pending', 'running', 'completed', 'failed')),

    -- Context at checkpoint (for replay)
    context_hash TEXT NOT NULL,
    context_summary TEXT,  -- Human-readable summary

    -- Timing
    started_at TIMESTAMP NOT NULL,
    finished_at TIMESTAMP,
    duration_ms INT,

    -- Metadata
    worker_count INT DEFAULT 0,
    failures INT DEFAULT 0,
    retries INT DEFAULT 0,
    error TEXT
);

CREATE INDEX IF NOT EXISTS idx_phase_conv ON phase_checkpoints(conversation_id, phase_number);


-- ============================================================================
-- Subagent Calls (Parallel Workers)
-- ============================================================================

CREATE TABLE IF NOT EXISTS subagent_calls (
    -- Idempotent key (for retries)
    call_key TEXT PRIMARY KEY,

    -- UUID for references
    id TEXT UNIQUE NOT NULL,

    -- Conversation context
    conversation_id TEXT NOT NULL REFERENCES conversations(id),
    phase TEXT NOT NULL,
    agent_type TEXT NOT NULL,

    -- LLM parameters (for deterministic replay)
    model_name TEXT NOT NULL,
    temperature FLOAT NOT NULL,
    top_p FLOAT,
    system_prompt TEXT,
    seed INT,
    provider_fingerprint TEXT NOT NULL,

    -- Payload references (external blobs for large content)
    prompt_ref TEXT NOT NULL,  -- SHA256 hash
    response_ref TEXT,         -- SHA256 hash

    -- Token & cost tracking (with reservation vs actual)
    tokens_in_reserved INT,    -- Initial reservation
    tokens_in_actual INT,      -- Actual after call
    tokens_out_actual INT,
    cost_usd FLOAT,

    -- Timing (observable)
    queued_at TIMESTAMP NOT NULL,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    queue_wait_ms INT,
    provider_latency_ms INT,
    total_duration_ms INT,

    -- Retry tracking
    retry_of TEXT REFERENCES subagent_calls(call_key),
    retry_count INT DEFAULT 0,

    -- Result
    finish_reason TEXT,
    error TEXT,

    -- Tracing (correlation IDs)
    correlation_id TEXT NOT NULL,
    span_id TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_subagent_conv_phase ON subagent_calls(conversation_id, phase);
CREATE INDEX IF NOT EXISTS idx_subagent_provider ON subagent_calls(provider_fingerprint, model_name);
CREATE INDEX IF NOT EXISTS idx_subagent_correlation ON subagent_calls(correlation_id);
CREATE INDEX IF NOT EXISTS idx_subagent_call_key ON subagent_calls(call_key);


-- ============================================================================
-- Blobs (External Storage with Deduplication)
-- ============================================================================

CREATE TABLE IF NOT EXISTS blobs (
    ref TEXT PRIMARY KEY,  -- SHA256 hash (deduplication key)
    kind TEXT NOT NULL
        CHECK(kind IN ('prompt', 'response', 'context', 'error', 'summary', 'session_summary')),

    -- Storage
    storage_url TEXT NOT NULL,  -- file:///path or s3://...
    size_bytes INT NOT NULL,
    content_preview TEXT,  -- First 500 chars (for quick inspection)

    -- Redaction metadata (PII protection)
    redacted BOOLEAN DEFAULT FALSE,
    redaction_rules_applied JSON,  -- List of rules applied
    preimage_hash TEXT,  -- HMAC of original content (for auditing)

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_blob_kind ON blobs(kind, created_at);
CREATE INDEX IF NOT EXISTS idx_blob_redacted ON blobs(redacted);


-- ============================================================================
-- Expert Responses (Domain Expert Outputs)
-- ============================================================================

CREATE TABLE IF NOT EXISTS expert_responses (
    id TEXT PRIMARY KEY,
    subagent_call_id TEXT NOT NULL REFERENCES subagent_calls(id),
    expert_type TEXT NOT NULL,

    -- Query/answer (refs to blobs)
    query_ref TEXT NOT NULL,
    answer_ref TEXT NOT NULL,

    -- Metadata
    confidence FLOAT CHECK(confidence >= 0 AND confidence <= 1),
    model_name TEXT,
    tokens_used INT,
    latency_ms INT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_expert_subagent ON expert_responses(subagent_call_id);
CREATE INDEX IF NOT EXISTS idx_expert_type ON expert_responses(expert_type);


-- ============================================================================
-- Metrics (Aggregated Analytics)
-- ============================================================================

CREATE TABLE IF NOT EXISTS metrics (
    id TEXT PRIMARY KEY,
    conversation_id TEXT REFERENCES conversations(id),

    -- Metric identity
    metric_name TEXT NOT NULL,
    metric_value FLOAT NOT NULL,

    -- Dimensions (for filtering and grouping)
    dimensions JSON,  -- {phase: "compile", provider: "anthropic", ...}

    -- Timestamps
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_metrics_name_time ON metrics(metric_name, recorded_at);
CREATE INDEX IF NOT EXISTS idx_metrics_conversation ON metrics(conversation_id);


-- ============================================================================
-- Configuration Snapshots (Immutable Per Conversation)
-- ============================================================================

CREATE TABLE IF NOT EXISTS config_snapshots (
    config_version TEXT PRIMARY KEY,
    config_json JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================================
-- Budget Reconciliation Log (Retry-Aware Accounting)
-- ============================================================================

CREATE TABLE IF NOT EXISTS budget_reconciliation (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id),
    call_key TEXT NOT NULL REFERENCES subagent_calls(call_key),

    -- Reconciliation details
    tokens_reserved INT NOT NULL,
    tokens_actual INT NOT NULL,
    tokens_delta INT NOT NULL,  -- actual - reserved

    -- Timestamps
    reconciled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_budget_conv ON budget_reconciliation(conversation_id);


-- ============================================================================
-- Boot Integrity Checks
-- ============================================================================

-- These views help detect inconsistencies that need repair on boot:

-- 1. Orphaned rotations (to_session_id without matching session)
CREATE VIEW IF NOT EXISTS v_orphaned_rotations AS
SELECT r.*
FROM session_rotations r
LEFT JOIN sessions s ON r.to_session_id = s.id
WHERE s.id IS NULL;

-- 2. Sessions stuck in rotating state (from crash)
CREATE VIEW IF NOT EXISTS v_stuck_rotations AS
SELECT *
FROM sessions
WHERE status IN ('rotating', 'summarizing')
  AND (rotation_started_at IS NOT NULL
       AND EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - rotation_started_at)) > 300);  -- 5 min timeout

-- 3. Active sessions without recent token usage (abandoned)
CREATE VIEW IF NOT EXISTS v_abandoned_sessions AS
SELECT s.*
FROM sessions s
LEFT JOIN session_token_usage u ON s.id = u.session_id
WHERE s.status = 'active'
  AND s.created_at < CURRENT_TIMESTAMP - INTERVAL '1 hour'
  AND (u.call_timestamp IS NULL
       OR u.call_timestamp < CURRENT_TIMESTAMP - INTERVAL '30 minutes');

-- 4. Sessions with token accounting mismatch
CREATE VIEW IF NOT EXISTS v_token_accounting_mismatch AS
SELECT
    s.id,
    s.tokens_spent AS session_tokens,
    COALESCE(SUM(u.tokens_total), 0) AS sum_usage_tokens,
    ABS(s.tokens_spent - COALESCE(SUM(u.tokens_total), 0)) AS delta
FROM sessions s
LEFT JOIN session_token_usage u ON s.id = u.session_id
GROUP BY s.id, s.tokens_spent
HAVING ABS(s.tokens_spent - COALESCE(SUM(u.tokens_total), 0)) > 100;  -- Allow 100 token variance


-- ============================================================================
-- Analytics Queries (Pre-defined for observability)
-- ============================================================================

-- Rotation performance summary
CREATE VIEW IF NOT EXISTS v_rotation_performance AS
SELECT
    trigger,
    COUNT(*) as rotation_count,
    AVG(handoff_duration_ms) as avg_handoff_ms,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY handoff_duration_ms) as p50_handoff_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY handoff_duration_ms) as p95_handoff_ms,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY handoff_duration_ms) as p99_handoff_ms,
    AVG(compression_ratio) as avg_compression,
    COUNT(CASE WHEN failure_reason IS NOT NULL THEN 1 END) as failure_count,
    COUNT(CASE WHEN fallback_used THEN 1 END) as fallback_count
FROM session_rotations
GROUP BY trigger;

-- Session health summary
CREATE VIEW IF NOT EXISTS v_session_health AS
SELECT
    status,
    COUNT(*) as session_count,
    AVG(tokens_spent) as avg_tokens,
    AVG(token_utilization_pct) as avg_utilization,
    COUNT(CASE WHEN token_utilization_pct >= 70 THEN 1 END) as high_utilization_count
FROM sessions
GROUP BY status;

-- Token usage trends
CREATE VIEW IF NOT EXISTS v_token_usage_trends AS
SELECT
    DATE_TRUNC('hour', call_timestamp) as hour,
    tool_name,
    COUNT(*) as call_count,
    SUM(tokens_total) as total_tokens,
    AVG(tokens_total) as avg_tokens_per_call,
    MAX(cumulative_tokens) as max_cumulative
FROM session_token_usage
GROUP BY hour, tool_name
ORDER BY hour DESC, total_tokens DESC;
