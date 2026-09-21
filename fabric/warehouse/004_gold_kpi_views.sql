-- Stage 3.12 — Gold KPI and Power BI consumption views

CREATE VIEW mart.v_oee_daily
AS
SELECT
    d.calendar_date,
    d.calendar_year,
    d.month_number,
    d.month_name,
    p.plant_id,
    p.plant_name,
    l.line_id,
    l.line_name,
    s.shift_id,
    s.shift_name,
    SUM(f.planned_production_seconds) AS planned_production_seconds,
    SUM(f.planned_stop_seconds) AS planned_stop_seconds,
    SUM(f.run_time_seconds) AS run_time_seconds,
    SUM(f.downtime_seconds) AS downtime_seconds,
    SUM(f.total_quantity) AS total_quantity,
    SUM(f.good_quantity) AS good_quantity,
    SUM(f.rejected_quantity) AS rejected_quantity,
    SUM(f.ideal_production_seconds) AS ideal_production_seconds,
    CASE
        WHEN SUM(f.planned_production_seconds) <= 0 THEN NULL
        ELSE 100.0 * SUM(f.run_time_seconds) / SUM(f.planned_production_seconds)
    END AS availability_pct,
    CASE
        WHEN SUM(f.run_time_seconds) <= 0 THEN NULL
        ELSE 100.0 * SUM(f.ideal_production_seconds) / SUM(f.run_time_seconds)
    END AS performance_pct,
    CASE
        WHEN SUM(f.total_quantity) <= 0 THEN NULL
        ELSE 100.0 * SUM(f.good_quantity) / SUM(f.total_quantity)
    END AS quality_pct,
    CASE
        WHEN SUM(f.planned_production_seconds) <= 0
          OR SUM(f.run_time_seconds) <= 0
          OR SUM(f.total_quantity) <= 0
        THEN NULL
        ELSE
            (
                100.0 * SUM(f.run_time_seconds) / SUM(f.planned_production_seconds)
            ) *
            (
                100.0 * SUM(f.ideal_production_seconds) / SUM(f.run_time_seconds)
            ) *
            (
                100.0 * SUM(f.good_quantity) / SUM(f.total_quantity)
            ) / 10000.0
    END AS oee_pct
FROM gold.fact_oee_daily f
JOIN gold.dim_date d ON d.date_sk = f.date_sk
JOIN gold.dim_plant p ON p.plant_sk = f.plant_sk
JOIN gold.dim_line l ON l.line_sk = f.line_sk
JOIN gold.dim_shift s ON s.shift_sk = f.shift_sk
GROUP BY
    d.calendar_date, d.calendar_year, d.month_number, d.month_name,
    p.plant_id, p.plant_name,
    l.line_id, l.line_name,
    s.shift_id, s.shift_name;
GO

CREATE VIEW mart.v_oee_by_machine
AS
SELECT
    d.calendar_date,
    p.plant_id,
    l.line_id,
    m.machine_id,
    m.machine_type_code,
    s.shift_id,
    f.planned_production_seconds,
    f.planned_stop_seconds,
    f.run_time_seconds,
    f.downtime_seconds,
    f.total_quantity,
    f.good_quantity,
    f.rejected_quantity,
    f.availability_pct,
    f.performance_pct,
    f.quality_pct,
    f.oee_pct
FROM gold.fact_oee_daily f
JOIN gold.dim_date d ON d.date_sk = f.date_sk
JOIN gold.dim_plant p ON p.plant_sk = f.plant_sk
JOIN gold.dim_line l ON l.line_sk = f.line_sk
LEFT JOIN gold.dim_machine m ON m.machine_sk = COALESCE(f.machine_sk, 0)
JOIN gold.dim_shift s ON s.shift_sk = f.shift_sk;
GO

CREATE VIEW mart.v_production_daily
AS
SELECT
    d.calendar_date,
    p.plant_id,
    p.plant_name,
    l.line_id,
    l.line_name,
    s.shift_id,
    pr.product_id,
    pr.product_name,
    f.event_type,
    SUM(COALESCE(f.actual_quantity, 0)) AS actual_quantity,
    SUM(COALESCE(f.good_quantity, 0)) AS good_quantity,
    SUM(COALESCE(f.rejected_quantity, 0)) AS rejected_quantity,
    SUM(COALESCE(f.loss_quantity, 0)) AS loss_quantity,
    SUM(COALESCE(f.loss_duration_seconds, 0)) AS loss_duration_seconds,
    COUNT_BIG(*) AS event_count
FROM gold.fact_production_event f
JOIN gold.dim_date d ON d.date_sk = f.date_sk
JOIN gold.dim_plant p ON p.plant_sk = f.plant_sk
LEFT JOIN gold.dim_line l ON l.line_sk = COALESCE(f.line_sk, 0)
JOIN gold.dim_shift s ON s.shift_sk = f.shift_sk
LEFT JOIN gold.dim_product pr ON pr.product_sk = COALESCE(f.product_sk, 0)
GROUP BY
    d.calendar_date, p.plant_id, p.plant_name,
    l.line_id, l.line_name, s.shift_id,
    pr.product_id, pr.product_name, f.event_type;
GO

CREATE VIEW mart.v_downtime_daily
AS
SELECT
    d.calendar_date,
    p.plant_id,
    l.line_id,
    m.machine_id,
    m.machine_type_code,
    s.shift_id,
    f.state_code,
    f.downtime_category,
    f.is_planned,
    SUM(f.duration_seconds) AS downtime_seconds,
    COUNT_BIG(*) AS interval_count
FROM gold.fact_downtime_interval f
JOIN gold.dim_date d ON d.date_sk = f.date_sk
JOIN gold.dim_plant p ON p.plant_sk = f.plant_sk
JOIN gold.dim_line l ON l.line_sk = f.line_sk
JOIN gold.dim_machine m ON m.machine_sk = f.machine_sk
JOIN gold.dim_shift s ON s.shift_sk = f.shift_sk
GROUP BY
    d.calendar_date, p.plant_id, l.line_id,
    m.machine_id, m.machine_type_code,
    s.shift_id, f.state_code, f.downtime_category, f.is_planned;
GO

CREATE VIEW mart.v_machine_health_latest
AS
WITH ranked AS (
    SELECT
        f.event_id,
        f.event_time_utc,
        p.plant_id,
        l.line_id,
        m.machine_id,
        m.machine_type_code,
        f.operating_state,
        f.temperature_c,
        f.vibration_mm_s,
        f.pressure_bar,
        f.power_kw,
        f.production_rate_unit_min,
        f.quality_score_pct,
        f.defect_probability_pct,
        f.ingestion_batch_id,
        f.simulator_run_id,
        f.scenario_id,
        f.scenario_instance_id,
        f.generation_sequence,
        ROW_NUMBER() OVER (
            PARTITION BY f.machine_sk
            ORDER BY f.event_time_utc DESC, f.generation_sequence DESC, f.event_id DESC
        ) AS row_rank
    FROM gold.fact_machine_telemetry f
    JOIN gold.dim_plant p ON p.plant_sk = f.plant_sk
    JOIN gold.dim_line l ON l.line_sk = f.line_sk
    JOIN gold.dim_machine m ON m.machine_sk = f.machine_sk
)
SELECT
    event_id,
    event_time_utc,
    plant_id,
    line_id,
    machine_id,
    machine_type_code,
    operating_state,
    temperature_c,
    vibration_mm_s,
    pressure_bar,
    power_kw,
    production_rate_unit_min,
    quality_score_pct,
    defect_probability_pct,
    ingestion_batch_id,
    simulator_run_id,
    scenario_id,
    scenario_instance_id,
    generation_sequence
FROM ranked
WHERE row_rank = 1;
GO

CREATE VIEW mart.v_operational_incidents
AS
SELECT
    d.calendar_date,
    p.plant_id,
    l.line_id,
    m.machine_id,
    m.machine_type_code,
    s.shift_id,
    f.event_type,
    f.severity,
    f.fault_code,
    fm.failure_mode_code,
    fm.failure_name,
    ac.alarm_code,
    ac.alarm_name,
    f.event_time_utc,
    f.is_planned,
    f.work_order_id,
    f.scenario_id,
    f.scenario_instance_id
FROM gold.fact_machine_operational_event f
JOIN gold.dim_date d ON d.date_sk = f.date_sk
JOIN gold.dim_plant p ON p.plant_sk = f.plant_sk
JOIN gold.dim_line l ON l.line_sk = f.line_sk
JOIN gold.dim_machine m ON m.machine_sk = f.machine_sk
JOIN gold.dim_shift s ON s.shift_sk = f.shift_sk
LEFT JOIN gold.dim_failure_mode fm ON fm.failure_mode_sk = COALESCE(f.failure_mode_sk, 0)
LEFT JOIN gold.dim_alarm_code ac ON ac.alarm_code_sk = COALESCE(f.alarm_sk, 0)
WHERE f.event_type IN (
    'AlarmRaised',
    'MachineFaulted',
    'CommunicationLost'
);
GO

CREATE VIEW mart.v_maintenance_summary
AS
SELECT
    d.calendar_date,
    p.plant_id,
    l.line_id,
    m.machine_id,
    f.event_type,
    f.maintenance_type,
    fm.failure_mode_code,
    fm.failure_name,
    COUNT_BIG(*) AS maintenance_event_count,
    SUM(COALESCE(f.quantity_consumed, 0)) AS spare_part_quantity_consumed
FROM gold.fact_maintenance_event f
JOIN gold.dim_date d ON d.date_sk = f.date_sk
JOIN gold.dim_plant p ON p.plant_sk = f.plant_sk
LEFT JOIN gold.dim_line l ON l.line_sk = COALESCE(f.line_sk, 0)
LEFT JOIN gold.dim_machine m ON m.machine_sk = COALESCE(f.machine_sk, 0)
LEFT JOIN gold.dim_failure_mode fm ON fm.failure_mode_sk = COALESCE(f.failure_mode_sk, 0)
GROUP BY
    d.calendar_date, p.plant_id, l.line_id, m.machine_id,
    f.event_type, f.maintenance_type,
    fm.failure_mode_code, fm.failure_name;
GO

CREATE VIEW mart.v_quality_summary
AS
SELECT
    d.calendar_date,
    p.plant_id,
    l.line_id,
    m.machine_id,
    pr.product_id,
    q.defect_code,
    q.defect_name,
    f.event_type,
    f.severity,
    f.disposition,
    COUNT_BIG(*) AS quality_event_count,
    AVG(f.measurement_value) AS average_measurement_value
FROM gold.fact_quality_event f
JOIN gold.dim_date d ON d.date_sk = f.date_sk
JOIN gold.dim_plant p ON p.plant_sk = f.plant_sk
LEFT JOIN gold.dim_line l ON l.line_sk = COALESCE(f.line_sk, 0)
LEFT JOIN gold.dim_machine m ON m.machine_sk = COALESCE(f.machine_sk, 0)
LEFT JOIN gold.dim_product pr ON pr.product_sk = COALESCE(f.product_sk, 0)
LEFT JOIN gold.dim_quality_defect q ON q.defect_sk = COALESCE(f.defect_sk, 0)
GROUP BY
    d.calendar_date, p.plant_id, l.line_id, m.machine_id,
    pr.product_id, q.defect_code, q.defect_name,
    f.event_type, f.severity, f.disposition;
GO
