-- Stage 3.16 — Predictive maintenance Gold prediction surface

CREATE TABLE gold.fact_machine_failure_prediction (
    prediction_fact_key BIGINT IDENTITY,
    prediction_id VARCHAR(64) NOT NULL,
    feature_id VARCHAR(64) NOT NULL,
    date_sk INT NOT NULL,
    shift_sk BIGINT NULL,
    plant_sk BIGINT NOT NULL,
    line_sk BIGINT NOT NULL,
    machine_sk BIGINT NOT NULL,
    feature_time_utc DATETIME2(3) NOT NULL,
    scored_at_utc DATETIME2(3) NOT NULL,
    model_name VARCHAR(150) NOT NULL,
    model_version VARCHAR(40) NOT NULL,
    feature_version VARCHAR(40) NOT NULL,
    prediction_horizon_minutes INT NOT NULL,
    failure_risk_score DECIMAL(9,6) NOT NULL,
    risk_band VARCHAR(20) NOT NULL,
    inference_mode VARCHAR(20) NOT NULL,
    endpoint_reference VARCHAR(500) NULL,
    source_run_id VARCHAR(100) NULL,
    created_at_utc DATETIME2(3) NOT NULL
);

GO

CREATE VIEW mart.v_machine_failure_risk_latest
AS
WITH ranked AS (
    SELECT
        p.*,
        ROW_NUMBER() OVER (
            PARTITION BY p.machine_sk
            ORDER BY p.feature_time_utc DESC, p.scored_at_utc DESC, p.prediction_id DESC
        ) AS rn
    FROM gold.fact_machine_failure_prediction AS p
)
SELECT
    prediction_fact_key,
    prediction_id,
    feature_id,
    date_sk,
    shift_sk,
    plant_sk,
    line_sk,
    machine_sk,
    feature_time_utc,
    scored_at_utc,
    model_name,
    model_version,
    feature_version,
    prediction_horizon_minutes,
    failure_risk_score,
    risk_band,
    inference_mode,
    endpoint_reference,
    source_run_id
FROM ranked
WHERE rn = 1;

GO

CREATE VIEW mart.v_machine_failure_risk_history
AS
SELECT
    date_sk,
    plant_sk,
    line_sk,
    machine_sk,
    feature_time_utc,
    scored_at_utc,
    model_name,
    model_version,
    feature_version,
    prediction_horizon_minutes,
    failure_risk_score,
    risk_band,
    inference_mode
FROM gold.fact_machine_failure_prediction;
