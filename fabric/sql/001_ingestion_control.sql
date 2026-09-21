-- Fabric ingestion control plane
-- No primary-key assumptions: idempotency is enforced by pipeline logic and MERGE conditions.

CREATE SCHEMA control;

CREATE TABLE control.ingestion_batch_checkpoint (
    idempotency_key VARCHAR(64) NOT NULL,
    ingestion_batch_id VARCHAR(68) NOT NULL,
    simulator_run_id VARCHAR(40) NOT NULL,
    source_file_path VARCHAR(2000) NOT NULL,
    source_file_sha256 VARCHAR(64) NOT NULL,
    event_type VARCHAR(32) NOT NULL,
    event_date DATE NOT NULL,
    plant_id VARCHAR(20) NOT NULL,
    event_count BIGINT NOT NULL,
    first_generation_sequence BIGINT NULL,
    last_generation_sequence BIGINT NULL,
    status VARCHAR(32) NOT NULL,
    accepted_event_count BIGINT NOT NULL,
    rejected_event_count BIGINT NOT NULL,
    error_code VARCHAR(100) NULL,
    created_at_utc DATETIME2 NOT NULL,
    updated_at_utc DATETIME2 NOT NULL
);

CREATE TABLE control.ingestion_event_log (
    event_id VARCHAR(50) NOT NULL,
    payload_sha256 VARCHAR(64) NOT NULL,
    ingestion_batch_id VARCHAR(68) NOT NULL,
    simulator_run_id VARCHAR(40) NOT NULL,
    status VARCHAR(32) NOT NULL,
    first_seen_at_utc DATETIME2 NOT NULL,
    last_seen_at_utc DATETIME2 NOT NULL
);

-- Recommended idempotency condition for batch upsert:
-- MERGE on ingestion_batch_id and source_file_sha256.
-- Recommended event idempotency condition:
-- MERGE on event_id; classify equal payload_sha256 as duplicate and differing hash as conflict.