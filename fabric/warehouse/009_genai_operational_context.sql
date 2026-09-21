-- Stage 3.18 — structured context surfaces for grounded GenAI/RAG

CREATE VIEW mart.v_genai_machine_context_latest
AS
WITH ranked_telemetry AS (
    SELECT
        t.*,
        ROW_NUMBER() OVER (
            PARTITION BY t.machine_sk
            ORDER BY t.event_time_utc DESC
        ) AS rn
    FROM gold.fact_machine_telemetry AS t
)
SELECT
    m.machine_id,
    m.machine_type_code,
    l.line_id,
    p.plant_id,
    t.event_time_utc,
    t.operating_state,
    t.temperature_c,
    t.vibration_mm_s,
    t.power_kw,
    t.quality_score_pct,
    r.failure_risk_score,
    r.risk_band,
    r.model_name,
    r.model_version
FROM ranked_telemetry AS t
JOIN gold.dim_machine AS m
  ON t.machine_sk = m.machine_sk
JOIN gold.dim_line AS l
  ON t.line_sk = l.line_sk
JOIN gold.dim_plant AS p
  ON t.plant_sk = p.plant_sk
LEFT JOIN mart.v_machine_failure_risk_latest AS r
  ON t.machine_sk = r.machine_sk
WHERE t.rn = 1;

GO

CREATE VIEW mart.v_genai_incident_context
AS
SELECT
    m.machine_id,
    p.plant_id,
    l.line_id,
    e.event_id,
    e.event_type,
    e.event_time_utc,
    e.severity,
    e.alarm_sk,
    e.failure_mode_sk,
    e.fault_code
FROM gold.fact_machine_operational_event AS e
JOIN gold.dim_machine AS m
  ON e.machine_sk = m.machine_sk
JOIN gold.dim_line AS l
  ON e.line_sk = l.line_sk
JOIN gold.dim_plant AS p
  ON e.plant_sk = p.plant_sk;

GO

CREATE VIEW mart.v_genai_production_context
AS
SELECT
    p.plant_sk,
    p.line_sk,
    p.machine_sk,
    p.product_sk,
    p.event_time_utc,
    p.actual_quantity,
    p.good_quantity,
    p.rejected_quantity,
    p.loss_quantity,
    p.loss_category,
    p.loss_reason_code
FROM gold.fact_production_event AS p;

GO

CREATE VIEW mart.v_genai_maintenance_context
AS
SELECT
    m.machine_id,
    p.plant_id,
    l.line_id,
    e.work_order_id,
    e.event_type,
    e.event_time_utc
FROM gold.fact_maintenance_event AS e
JOIN gold.dim_machine AS m
  ON e.machine_sk = m.machine_sk
JOIN gold.dim_line AS l
  ON e.line_sk = l.line_sk
JOIN gold.dim_plant AS p
  ON e.plant_sk = p.plant_sk;
