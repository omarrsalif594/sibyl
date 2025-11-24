-- Production schema for LLM orchestration state store (DuckDB)
-- Version: 2

-- ============================================================================
-- Schema Version Tracking
-- ============================================================================

CREATE TABLE IF NOT EXISTS schema_version (
    version INT PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT NOT NULL
);

-- Insert initial version
INSERT OR IGNORE INTO schema_version (version, description)
VALUES (1, 'Initial schema');


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
        CHECK(kind IN ('prompt', 'response', 'context', 'error', 'summary')),

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
