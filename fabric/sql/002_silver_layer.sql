-- Stage 3.11 — Silver Lakehouse control/audit model
-- Silver domain tables are created by the Fabric Spark transformation notebook.

CREATE SCHEMA control;

CREATE TABLE control.silver_load_audit (
    silver_run_id VARCHAR(68) NOT NULL,
    processing_started_at_utc DATETIME2 NOT NULL,
    processing_completed_at_utc DATETIME2 NULL,
    source_table VARCHAR(200) NOT NULL,
    source_window_start_utc DATETIME2 NULL,
    source_window_end_utc DATETIME2 NULL,
    source_row_count BIGINT NOT NULL,
    duplicate_row_count BIGINT NOT NULL,
    conflict_event_count BIGINT NOT NULL,
    accepted_row_count BIGINT NOT NULL,
    rejected_row_count BIGINT NOT NULL,
    late_arrival_count BIGINT NOT NULL,
    master_reference_failure_count BIGINT NOT NULL,
    status VARCHAR(32) NOT NULL,
    error_code VARCHAR(100) NULL,
    details VARCHAR(4000) NULL
);

CREATE SCHEMA silver;

CREATE TABLE silver.rejected_event (
    silver_run_id VARCHAR(68) NOT NULL,
    event_id VARCHAR(50) NULL,
    event_type VARCHAR(100) NULL,
    rejection_code VARCHAR(100) NOT NULL,
    rejection_detail VARCHAR(2000) NULL,
    ingestion_batch_id VARCHAR(68) NULL,
    simulator_run_id VARCHAR(40) NULL,
    event_time DATETIME2 NULL,
    ingestion_time DATETIME2 NULL,
    event_payload_json VARCHAR(MAX) NULL,
    rejected_at_utc DATETIME2 NOT NULL
);

-- Silver domain tables are Delta tables created/managed by Spark:
-- silver.machine_telemetry
-- silver.machine_operational_event
-- silver.production_event

-- The load notebook uses event_id as the business identity and event payload hash
-- for conflict detection. No database PK/FK is assumed.