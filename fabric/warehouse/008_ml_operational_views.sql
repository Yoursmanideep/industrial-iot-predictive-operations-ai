-- Stage 3.17 — ML monitoring, explainability and operational decision surface

CREATE TABLE gold.fact_ml_model_monitoring (
    monitoring_fact_key BIGINT IDENTITY,
    model_name VARCHAR(150) NOT NULL,
    model_version VARCHAR(40) NOT NULL,
    monitor_window_start_utc DATETIME2(3) NOT NULL,
    monitor_window_end_utc DATETIME2(3) NOT NULL,
    metric_name VARCHAR(80) NOT NULL,
    metric_value DECIMAL(18,8) NULL,
    threshold_value DECIMAL(18,8) NULL,
    status VARCHAR(20) NOT NULL,
    action VARCHAR(60) NOT NULL,
    feature_version VARCHAR(40) NOT NULL,
    created_at_utc DATETIME2(3) NOT NULL
);

GO

CREATE TABLE gold.fact_ml_feature_explanation (
    explanation_fact_key BIGINT IDENTITY,
    model_name VARCHAR(150) NOT NULL,
    model_version VARCHAR(40) NOT NULL,
    feature_name VARCHAR(150) NOT NULL,
    feature_importance DECIMAL(18,10) NOT NULL,
    importance_rank INT NOT NULL,
    explanation_method VARCHAR(80) NOT NULL,
    feature_version VARCHAR(40) NOT NULL,
    created_at_utc DATETIME2(3) NOT NULL
);

GO

CREATE VIEW mart.v_ml_model_health
AS
SELECT
    model_name,
    model_version,
    monitor_window_start_utc,
    monitor_window_end_utc,
    metric_name,
    metric_value,
    threshold_value,
    status,
    action,
    feature_version,
    created_at_utc
FROM gold.fact_ml_model_monitoring;

GO

CREATE VIEW mart.v_ml_feature_importance
AS
SELECT
    model_name,
    model_version,
    feature_name,
    feature_importance,
    importance_rank,
    explanation_method,
    feature_version,
    created_at_utc
FROM gold.fact_ml_feature_explanation
WHERE importance_rank <= 15;

GO

CREATE VIEW mart.v_ml_actionable_machine_risk
AS
WITH latest_prediction AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY machine_sk
            ORDER BY feature_time_utc DESC, scored_at_utc DESC, prediction_id DESC
        ) AS rn
    FROM gold.fact_machine_failure_prediction
)
SELECT
    p.prediction_id,
    p.plant_sk,
    p.line_sk,
    p.machine_sk,
    p.feature_time_utc,
    p.scored_at_utc,
    p.model_name,
    p.model_version,
    p.failure_risk_score,
    p.risk_band,
    p.inference_mode
FROM latest_prediction p
WHERE rn = 1
  AND p.risk_band IN ('HIGH', 'CRITICAL');
