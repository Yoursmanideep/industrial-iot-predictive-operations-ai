-- Stage 3.12 — Gold fact loading and OEE calculation

DROP PROCEDURE IF EXISTS gold.usp_load_facts;
GO

CREATE PROCEDURE gold.usp_load_facts
    @source_window_start_utc DATETIME2(3),
    @source_window_end_utc DATETIME2(3)
AS
BEGIN
    -- Machine telemetry fact
    MERGE gold.fact_machine_telemetry AS target
    USING (
        SELECT
            s.event_id,
            sc.business_date_sk AS date_sk,
            sc.shift_sk,
            l.plant_sk,
            m.line_sk,
            m.machine_sk,
            m.machine_model_sk,
            s.event_time AS event_time_utc,
            s.ingestion_time AS ingestion_time_utc,
            s.operating_state,
            s.temperature_c, s.vibration_mm_s, s.pressure_bar, s.spindle_rpm, s.power_kw,
            s.production_rate_unit_min, s.quality_score_pct, s.feed_rate_mm_min,
            s.hydraulic_pressure_bar, s.force_kn, s.cycle_time_s, s.motor_temperature_c,
            s.torque_nm, s.position_error_mm, s.motor_current_a, s.belt_speed_m_s,
            s.discharge_pressure_bar, s.rpm, s.chamber_temperature_c, s.fuel_flow_rate,
            s.pressure_mbar, s.inspection_cycle_time_s, s.measurement_deviation_mm,
            s.defect_probability_pct, s.equipment_temperature_c, s.throughput_unit_min,
            s.is_late_arrival, s.ingestion_batch_id, s.simulator_run_id, s.scenario_id,
            s.scenario_instance_id, s.generation_sequence, s.payload_sha256
        FROM stg.silver_machine_telemetry s
        JOIN gold.dim_machine m
          ON m.machine_id = s.machine_id
         AND CAST(s.event_time AS DATE) >= m.effective_from
         AND (m.effective_to IS NULL OR CAST(s.event_time AS DATE) <= m.effective_to)
        JOIN gold.dim_line l
          ON l.line_sk = m.line_sk
         AND CAST(s.event_time AS DATE) >= l.effective_from
         AND (l.effective_to IS NULL OR CAST(s.event_time AS DATE) <= l.effective_to)
        JOIN gold.dim_shift_calendar sc
          ON s.event_time >= sc.shift_start_utc
         AND s.event_time < sc.shift_end_utc
        WHERE s.event_time >= @source_window_start_utc
          AND s.event_time < @source_window_end_utc
    ) AS source
    ON target.event_id = source.event_id
    WHEN NOT MATCHED THEN
        INSERT (
            event_id, date_sk, shift_sk, plant_sk, line_sk, machine_sk, machine_model_sk,
            event_time_utc, ingestion_time_utc, operating_state, temperature_c, vibration_mm_s,
            pressure_bar, spindle_rpm, power_kw, production_rate_unit_min, quality_score_pct,
            feed_rate_mm_min, hydraulic_pressure_bar, force_kn, cycle_time_s, motor_temperature_c,
            torque_nm, position_error_mm, motor_current_a, belt_speed_m_s, discharge_pressure_bar,
            rpm, chamber_temperature_c, fuel_flow_rate, pressure_mbar, inspection_cycle_time_s,
            measurement_deviation_mm, defect_probability_pct, equipment_temperature_c,
            throughput_unit_min, is_late_arrival, ingestion_batch_id, simulator_run_id,
            scenario_id, scenario_instance_id, generation_sequence, payload_sha256
        )
        VALUES (
            source.event_id, source.date_sk, source.shift_sk, source.plant_sk, source.line_sk,
            source.machine_sk, source.machine_model_sk, source.event_time_utc,
            source.ingestion_time_utc, source.operating_state, source.temperature_c,
            source.vibration_mm_s, source.pressure_bar, source.spindle_rpm, source.power_kw,
            source.production_rate_unit_min, source.quality_score_pct, source.feed_rate_mm_min,
            source.hydraulic_pressure_bar, source.force_kn, source.cycle_time_s,
            source.motor_temperature_c, source.torque_nm, source.position_error_mm,
            source.motor_current_a, source.belt_speed_m_s, source.discharge_pressure_bar,
            source.rpm, source.chamber_temperature_c, source.fuel_flow_rate, source.pressure_mbar,
            source.inspection_cycle_time_s, source.measurement_deviation_mm,
            source.defect_probability_pct, source.equipment_temperature_c, source.throughput_unit_min,
            source.is_late_arrival, source.ingestion_batch_id, source.simulator_run_id,
            source.scenario_id, source.scenario_instance_id, source.generation_sequence,
            source.payload_sha256
        );

    -- Machine operational event fact
    MERGE gold.fact_machine_operational_event AS target
    USING (
        SELECT
            s.event_id,
            sc.business_date_sk AS date_sk,
            sc.shift_sk,
            l.plant_sk,
            m.line_sk,
            m.machine_sk,
            s.event_type,
            s.event_time AS event_time_utc,
            s.operating_state, s.previous_state, s.new_state,
            COALESCE(a.alarm_code_sk, 0) AS alarm_sk,
            COALESCE(f.failure_mode_sk, 0) AS failure_mode_sk,
            COALESCE(o.operator_sk, 0) AS operator_sk,
            s.severity, s.fault_code, s.operator_id, s.work_order_id,
            s.is_planned, s.estimated_duration_seconds, s.communication_gap_seconds,
            s.is_late_arrival, s.ingestion_batch_id, s.simulator_run_id, s.scenario_id,
            s.scenario_instance_id, s.generation_sequence, s.payload_sha256
        FROM stg.silver_machine_operational_event s
        JOIN gold.dim_machine m
          ON m.machine_id = s.machine_id
         AND CAST(s.event_time AS DATE) >= m.effective_from
         AND (m.effective_to IS NULL OR CAST(s.event_time AS DATE) <= m.effective_to)
        JOIN gold.dim_line l
          ON l.line_sk = m.line_sk
         AND CAST(s.event_time AS DATE) >= l.effective_from
         AND (l.effective_to IS NULL OR CAST(s.event_time AS DATE) <= l.effective_to)
        JOIN gold.dim_shift_calendar sc
          ON s.event_time >= sc.shift_start_utc
         AND s.event_time < sc.shift_end_utc
        LEFT JOIN gold.dim_alarm_code a ON a.alarm_code = COALESCE(s.alarm_code, 'UNKNOWN')
        LEFT JOIN gold.dim_failure_mode f ON f.failure_mode_code = COALESCE(s.failure_mode_code, 'UNKNOWN')
        LEFT JOIN gold.dim_operator o
          ON o.operator_id = COALESCE(s.operator_id, 'UNKNOWN')
         AND CAST(s.event_time AS DATE) >= o.effective_from
         AND (o.effective_to IS NULL OR CAST(s.event_time AS DATE) <= o.effective_to)
        WHERE s.event_time >= @source_window_start_utc
          AND s.event_time < @source_window_end_utc
    ) AS source
    ON target.event_id = source.event_id
    WHEN NOT MATCHED THEN
        INSERT (
            event_id, date_sk, shift_sk, plant_sk, line_sk, machine_sk, event_type,
            event_time_utc, operating_state, previous_state, new_state, alarm_sk,
            failure_mode_sk, operator_sk, severity, fault_code, operator_id, work_order_id,
            is_planned, estimated_duration_seconds, communication_gap_seconds, is_late_arrival,
            ingestion_batch_id, simulator_run_id, scenario_id, scenario_instance_id,
            generation_sequence, payload_sha256
        )
        VALUES (
            source.event_id, source.date_sk, source.shift_sk, source.plant_sk, source.line_sk,
            source.machine_sk, source.event_type, source.event_time_utc, source.operating_state,
            source.previous_state, source.new_state, source.alarm_sk, source.failure_mode_sk,
            source.operator_sk, source.severity, source.fault_code, source.operator_id,
            source.work_order_id, source.is_planned, source.estimated_duration_seconds,
            source.communication_gap_seconds, source.is_late_arrival, source.ingestion_batch_id,
            source.simulator_run_id, source.scenario_id, source.scenario_instance_id,
            source.generation_sequence, source.payload_sha256
        );

    -- Production event fact
    MERGE gold.fact_production_event AS target
    USING (
        SELECT
            s.event_id,
            sc.business_date_sk AS date_sk,
            sc.shift_sk,
            p.plant_sk,
            l.line_sk,
            m.machine_sk,
            pr.product_sk,
            s.production_order_id, s.batch_id, s.event_type, s.event_time AS event_time_utc,
            s.actual_quantity, s.good_quantity, s.rejected_quantity, s.planned_quantity,
            s.quantity_uom, s.loss_quantity, s.loss_duration_seconds, s.loss_category,
            s.loss_reason_code, s.downtime_event_id, s.machine_fault_event_id,
            s.is_late_arrival, s.ingestion_batch_id, s.simulator_run_id, s.scenario_id,
            s.scenario_instance_id, s.generation_sequence, s.payload_sha256
        FROM stg.silver_production_event s
        JOIN gold.dim_plant p
          ON p.plant_id = s.plant_id
         AND CAST(s.event_time AS DATE) >= p.effective_from
         AND (p.effective_to IS NULL OR CAST(s.event_time AS DATE) <= p.effective_to)
        LEFT JOIN gold.dim_line l
          ON l.line_id = COALESCE(s.line_id, 'UNKNOWN')
         AND CAST(s.event_time AS DATE) >= l.effective_from
         AND (l.effective_to IS NULL OR CAST(s.event_time AS DATE) <= l.effective_to)
        LEFT JOIN gold.dim_machine m
          ON m.machine_id = COALESCE(s.machine_id, 'UNKNOWN')
         AND CAST(s.event_time AS DATE) >= m.effective_from
         AND (m.effective_to IS NULL OR CAST(s.event_time AS DATE) <= m.effective_to)
        LEFT JOIN gold.dim_product pr
          ON pr.product_id = COALESCE(s.product_id, 'UNKNOWN')
         AND CAST(s.event_time AS DATE) >= pr.effective_from
         AND (pr.effective_to IS NULL OR CAST(s.event_time AS DATE) <= pr.effective_to)
        JOIN gold.dim_shift_calendar sc
          ON s.event_time >= sc.shift_start_utc
         AND s.event_time < sc.shift_end_utc
        WHERE s.event_time >= @source_window_start_utc
          AND s.event_time < @source_window_end_utc
    ) AS source
    ON target.event_id = source.event_id
    WHEN NOT MATCHED THEN
        INSERT (
            event_id, date_sk, shift_sk, plant_sk, line_sk, machine_sk, product_sk,
            production_order_id, batch_id, event_type, event_time_utc, actual_quantity,
            good_quantity, rejected_quantity, planned_quantity, quantity_uom, loss_quantity,
            loss_duration_seconds, loss_category, loss_reason_code, downtime_event_id,
            machine_fault_event_id, is_late_arrival, ingestion_batch_id, simulator_run_id,
            scenario_id, scenario_instance_id, generation_sequence, payload_sha256
        )
        VALUES (
            source.event_id, source.date_sk, source.shift_sk, source.plant_sk, source.line_sk,
            source.machine_sk, source.product_sk, source.production_order_id, source.batch_id,
            source.event_type, source.event_time_utc, source.actual_quantity, source.good_quantity,
            source.rejected_quantity, source.planned_quantity, source.quantity_uom,
            source.loss_quantity, source.loss_duration_seconds, source.loss_category,
            source.loss_reason_code, source.downtime_event_id, source.machine_fault_event_id,
            source.is_late_arrival, source.ingestion_batch_id, source.simulator_run_id,
            source.scenario_id, source.scenario_instance_id, source.generation_sequence,
            source.payload_sha256
        );

    -- Split machine state intervals across shift boundaries.
    MERGE gold.fact_downtime_interval AS target
    USING (
        WITH ranked_before_window AS (
            SELECT
                f.*,
                ROW_NUMBER() OVER (
                    PARTITION BY f.machine_sk
                    ORDER BY f.event_time_utc DESC, f.generation_sequence DESC, f.event_id DESC
                ) AS row_rank
            FROM gold.fact_machine_operational_event f
            WHERE f.event_type = 'StateChanged'
              AND f.event_time_utc < @source_window_start_utc
        ),
        candidate_changes AS (
            SELECT *
            FROM gold.fact_machine_operational_event
            WHERE event_type = 'StateChanged'
              AND event_time_utc >= @source_window_start_utc
              AND event_time_utc < @source_window_end_utc

            UNION ALL

            SELECT
                event_id, date_sk, shift_sk, plant_sk, line_sk, machine_sk, event_type,
                event_time_utc, operating_state, previous_state, new_state, alarm_sk,
                failure_mode_sk, operator_sk, severity, fault_code, operator_id, work_order_id,
                is_planned, estimated_duration_seconds, communication_gap_seconds, is_late_arrival,
                ingestion_batch_id, simulator_run_id, scenario_id, scenario_instance_id,
                generation_sequence, payload_sha256
            FROM ranked_before_window
            WHERE row_rank = 1
        ),
        state_changes AS (
            SELECT
                event_id AS start_event_id,
                LEAD(event_id) OVER (
                    PARTITION BY machine_sk
                    ORDER BY event_time_utc, generation_sequence, event_id
                ) AS end_event_id,
                event_time_utc AS interval_start_utc,
                LEAD(event_time_utc) OVER (
                    PARTITION BY machine_sk
                    ORDER BY event_time_utc, generation_sequence, event_id
                ) AS interval_end_utc,
                plant_sk, line_sk, machine_sk, new_state AS state_code, is_planned
            FROM candidate_changes
        ),
        intervals AS (
            SELECT *
            FROM state_changes
            WHERE interval_end_utc IS NOT NULL
              AND interval_end_utc > interval_start_utc
              AND interval_end_utc > @source_window_start_utc
              AND interval_start_utc < @source_window_end_utc
              AND state_code IN (
                  'FAULT', 'MAINTENANCE', 'OFFLINE', 'BLOCKED', 'STARVED', 'SETUP', 'IDLE'
              )
        )
        SELECT
            i.start_event_id,
            i.end_event_id,
            sc.business_date_sk AS date_sk,
            sc.shift_sk,
            i.plant_sk, i.line_sk, i.machine_sk,
            i.state_code,
            CASE
                WHEN i.is_planned = 1 AND i.state_code = 'MAINTENANCE' THEN 'PLANNED_MAINTENANCE'
                WHEN i.is_planned = 1 AND i.state_code = 'SETUP' THEN 'PLANNED_SETUP'
                WHEN i.is_planned = 1 AND i.state_code = 'IDLE' THEN 'PLANNED_IDLE'
                WHEN i.state_code = 'FAULT' THEN 'UNPLANNED_FAULT'
                WHEN i.state_code = 'OFFLINE' THEN 'UNPLANNED_OFFLINE'
                WHEN i.state_code = 'BLOCKED' THEN 'UNPLANNED_BLOCKED'
                WHEN i.state_code = 'STARVED' THEN 'UNPLANNED_STARVED'
                WHEN i.state_code = 'MAINTENANCE' THEN 'UNPLANNED_MAINTENANCE'
                WHEN i.state_code = 'SETUP' THEN 'UNPLANNED_SETUP'
                ELSE 'IDLE_NO_DEMAND'
            END AS downtime_category,
            COALESCE(i.is_planned, 0) AS is_planned,
            CASE
                WHEN i.interval_start_utc > sc.shift_start_utc AND i.interval_start_utc > @source_window_start_utc
                    THEN i.interval_start_utc
                WHEN sc.shift_start_utc > @source_window_start_utc
                    THEN sc.shift_start_utc
                ELSE @source_window_start_utc
            END AS overlap_start,
            CASE
                WHEN i.interval_end_utc < sc.shift_end_utc AND i.interval_end_utc < @source_window_end_utc
                    THEN i.interval_end_utc
                WHEN sc.shift_end_utc < @source_window_end_utc
                    THEN sc.shift_end_utc
                ELSE @source_window_end_utc
            END AS overlap_end
        FROM intervals i
        JOIN gold.dim_shift_calendar sc
          ON i.interval_start_utc < sc.shift_end_utc
         AND i.interval_end_utc > sc.shift_start_utc
    ) AS source
    ON target.start_event_id = source.start_event_id
   AND target.shift_sk = source.shift_sk
    WHEN NOT MATCHED THEN
        INSERT (
            start_event_id, end_event_id, date_sk, shift_sk, plant_sk, line_sk, machine_sk,
            state_code, downtime_category, is_planned, interval_start_utc, interval_end_utc,
            duration_seconds
        )
        WHEN MATCHED THEN
            UPDATE SET
                target.end_event_id = source.end_event_id,
                target.date_sk = source.date_sk,
                target.plant_sk = source.plant_sk,
                target.line_sk = source.line_sk,
                target.machine_sk = source.machine_sk,
                target.state_code = source.state_code,
                target.downtime_category = source.downtime_category,
                target.is_planned = source.is_planned,
                target.interval_start_utc = source.overlap_start,
                target.interval_end_utc = source.overlap_end,
                target.duration_seconds =
                    DATEDIFF(millisecond, source.overlap_start, source.overlap_end) / 1000.0

        -- Production loss fact is a narrow analytical subset of production losses.
    MERGE gold.fact_production_loss AS target
    USING (
        SELECT
            event_id, date_sk, shift_sk, plant_sk, line_sk, machine_sk, product_sk,
            loss_category, loss_reason_code,
            COALESCE(loss_quantity, 0) AS loss_quantity,
            loss_duration_seconds, event_time_utc
        FROM gold.fact_production_event
        WHERE event_type = 'ProductionLossRecorded'
          AND event_time_utc >= @source_window_start_utc
          AND event_time_utc < @source_window_end_utc
    ) AS source
    ON target.event_id = source.event_id
    WHEN NOT MATCHED THEN
        INSERT (
            event_id, date_sk, shift_sk, plant_sk, line_sk, machine_sk, product_sk,
            loss_category, loss_reason_code, loss_quantity, loss_duration_seconds, event_time_utc
        )
        VALUES (
            source.event_id, source.date_sk, source.shift_sk, source.plant_sk, source.line_sk,
            source.machine_sk, source.product_sk, source.loss_category, source.loss_reason_code,
            source.loss_quantity, source.loss_duration_seconds, source.event_time_utc
        );

    -- Maintenance events. Source staging remains empty until the maintenance Silver domain is enabled.
    MERGE gold.fact_maintenance_event AS target
    USING (
        SELECT
            s.event_id,
            sc.business_date_sk AS date_sk,
            sc.shift_sk,
            p.plant_sk,
            l.line_sk,
            m.machine_sk,
            s.work_order_id,
            t.technician_sk,
            s.event_type,
            s.maintenance_type,
            COALESCE(f.failure_mode_sk, 0) AS failure_mode_sk,
            sp.spare_part_sk,
            s.quantity_consumed,
            s.event_time AS event_time_utc,
            s.ingestion_batch_id,
            s.payload_sha256
        FROM stg.silver_maintenance_event s
        JOIN gold.dim_plant p
          ON p.plant_id = s.plant_id
        LEFT JOIN gold.dim_line l ON l.line_id = COALESCE(s.line_id, 'UNKNOWN')
        LEFT JOIN gold.dim_machine m ON m.machine_id = COALESCE(s.machine_id, 'UNKNOWN')
        LEFT JOIN gold.dim_technician t ON t.technician_id = COALESCE(s.technician_id, 'UNKNOWN')
        LEFT JOIN gold.dim_failure_mode f ON f.failure_mode_code = COALESCE(s.failure_mode_code, 'UNKNOWN')
        LEFT JOIN gold.dim_spare_part sp ON sp.part_id = COALESCE(s.spare_part_id, 'UNKNOWN')
        JOIN gold.dim_shift_calendar sc
          ON s.event_time >= sc.shift_start_utc
         AND s.event_time < sc.shift_end_utc
        WHERE s.event_time >= @source_window_start_utc
          AND s.event_time < @source_window_end_utc
    ) AS source
    ON target.event_id = source.event_id
    WHEN NOT MATCHED THEN
        INSERT (
            event_id, date_sk, shift_sk, plant_sk, line_sk, machine_sk, work_order_id,
            technician_sk, event_type, maintenance_type, failure_mode_sk, spare_part_sk,
            quantity_consumed, event_time_utc, ingestion_batch_id, payload_sha256
        )
        VALUES (
            source.event_id, source.date_sk, source.shift_sk, source.plant_sk, source.line_sk,
            source.machine_sk, source.work_order_id, source.technician_sk, source.event_type,
            source.maintenance_type, source.failure_mode_sk, source.spare_part_sk,
            source.quantity_consumed, source.event_time_utc, source.ingestion_batch_id,
            source.payload_sha256
        );

    -- Quality events. Source staging remains empty until the quality Silver domain is enabled.
    MERGE gold.fact_quality_event AS target
    USING (
        SELECT
            s.event_id,
            sc.business_date_sk AS date_sk,
            sc.shift_sk,
            p.plant_sk,
            l.line_sk,
            m.machine_sk,
            pr.product_sk,
            s.production_order_id,
            s.batch_id,
            s.event_type,
            COALESCE(q.defect_sk, 0) AS defect_sk,
            s.severity,
            s.measurement_value,
            s.measurement_uom,
            s.disposition,
            s.event_time AS event_time_utc,
            s.ingestion_batch_id,
            s.payload_sha256
        FROM stg.silver_quality_event s
        JOIN gold.dim_plant p ON p.plant_id = s.plant_id
        LEFT JOIN gold.dim_line l ON l.line_id = COALESCE(s.line_id, 'UNKNOWN')
        LEFT JOIN gold.dim_machine m ON m.machine_id = COALESCE(s.machine_id, 'UNKNOWN')
        LEFT JOIN gold.dim_product pr ON pr.product_id = COALESCE(s.product_id, 'UNKNOWN')
        LEFT JOIN gold.dim_quality_defect q ON q.defect_code = COALESCE(s.defect_code, 'UNKNOWN')
        JOIN gold.dim_shift_calendar sc
          ON s.event_time >= sc.shift_start_utc
         AND s.event_time < sc.shift_end_utc
        WHERE s.event_time >= @source_window_start_utc
          AND s.event_time < @source_window_end_utc
    ) AS source
    ON target.event_id = source.event_id
    WHEN NOT MATCHED THEN
        INSERT (
            event_id, date_sk, shift_sk, plant_sk, line_sk, machine_sk, product_sk,
            production_order_id, batch_id, event_type, defect_sk, severity,
            measurement_value, measurement_uom, disposition, event_time_utc,
            ingestion_batch_id, payload_sha256
        )
        VALUES (
            source.event_id, source.date_sk, source.shift_sk, source.plant_sk, source.line_sk,
            source.machine_sk, source.product_sk, source.production_order_id, source.batch_id,
            source.event_type, source.defect_sk, source.severity, source.measurement_value,
            source.measurement_uom, source.disposition, source.event_time_utc,
            source.ingestion_batch_id, source.payload_sha256
        );
END;
GO

DROP PROCEDURE IF EXISTS gold.usp_refresh_oee;
GO

CREATE PROCEDURE gold.usp_refresh_oee
    @business_date_start DATE,
    @business_date_end DATE
AS
BEGIN
    DELETE FROM gold.fact_oee_daily
    WHERE date_sk >= YEAR(@business_date_start) * 10000 + MONTH(@business_date_start) * 100 + DAY(@business_date_start)
      AND date_sk <= YEAR(@business_date_end) * 10000 + MONTH(@business_date_end) * 100 + DAY(@business_date_end);

    WITH scope AS (
        SELECT DISTINCT date_sk, shift_sk, plant_sk, line_sk, machine_sk
        FROM gold.fact_production_event
        WHERE date_sk BETWEEN
              YEAR(@business_date_start) * 10000 + MONTH(@business_date_start) * 100 + DAY(@business_date_start)
              AND YEAR(@business_date_end) * 10000 + MONTH(@business_date_end) * 100 + DAY(@business_date_end)
          AND event_type = 'UnitProduced'

        UNION

        SELECT DISTINCT date_sk, shift_sk, plant_sk, line_sk, machine_sk
        FROM gold.fact_downtime_interval
        WHERE date_sk BETWEEN
              YEAR(@business_date_start) * 10000 + MONTH(@business_date_start) * 100 + DAY(@business_date_start)
              AND YEAR(@business_date_end) * 10000 + MONTH(@business_date_end) * 100 + DAY(@business_date_end)
    ),
    production AS (
        SELECT
            f.date_sk, f.shift_sk, f.plant_sk, f.line_sk, f.machine_sk,
            SUM(COALESCE(f.actual_quantity, 0)) AS total_quantity,
            SUM(COALESCE(f.good_quantity, 0)) AS good_quantity,
            SUM(COALESCE(f.rejected_quantity, 0)) AS rejected_quantity,
            SUM(
                COALESCE(f.actual_quantity, 0) * COALESCE(p.standard_cycle_time_seconds, 0)
            ) AS ideal_production_seconds
        FROM gold.fact_production_event f
        LEFT JOIN gold.dim_product p ON p.product_sk = COALESCE(f.product_sk, 0)
        WHERE f.event_type = 'UnitProduced'
        GROUP BY f.date_sk, f.shift_sk, f.plant_sk, f.line_sk, f.machine_sk
    ),
    downtime AS (
        SELECT
            date_sk, shift_sk, plant_sk, line_sk, machine_sk,
            SUM(CASE WHEN is_planned = 1 THEN duration_seconds ELSE 0 END) AS planned_stop_seconds,
            SUM(CASE WHEN is_planned = 0 THEN duration_seconds ELSE 0 END) AS unplanned_downtime_seconds
        FROM gold.fact_downtime_interval
        GROUP BY date_sk, shift_sk, plant_sk, line_sk, machine_sk
    ),
    metrics AS (
        SELECT
            s.date_sk, s.shift_sk, s.plant_sk, s.line_sk, s.machine_sk,
            CAST(28800.0 AS DECIMAL(18,3)) AS scheduled_shift_seconds,
            COALESCE(d.planned_stop_seconds, 0) AS planned_stop_seconds,
            COALESCE(d.unplanned_downtime_seconds, 0) AS downtime_seconds,
            CAST(
                28800.0
                - COALESCE(d.planned_stop_seconds, 0)
                - COALESCE(d.unplanned_downtime_seconds, 0)
                AS DECIMAL(18,3)
            ) AS run_time_seconds,
            COALESCE(p.total_quantity, 0) AS total_quantity,
            COALESCE(p.good_quantity, 0) AS good_quantity,
            COALESCE(p.rejected_quantity, 0) AS rejected_quantity,
            COALESCE(p.ideal_production_seconds, 0) AS ideal_production_seconds
        FROM scope s
        LEFT JOIN production p
          ON p.date_sk = s.date_sk
         AND p.shift_sk = s.shift_sk
         AND p.plant_sk = s.plant_sk
         AND p.line_sk = s.line_sk
         AND ((p.machine_sk = s.machine_sk) OR (p.machine_sk IS NULL AND s.machine_sk IS NULL))
        LEFT JOIN downtime d
          ON d.date_sk = s.date_sk
         AND d.shift_sk = s.shift_sk
         AND d.plant_sk = s.plant_sk
         AND d.line_sk = s.line_sk
         AND d.machine_sk = s.machine_sk
    )
    INSERT INTO gold.fact_oee_daily (
        date_sk, shift_sk, plant_sk, line_sk, machine_sk,
        planned_production_seconds, planned_stop_seconds, run_time_seconds, downtime_seconds,
        total_quantity, good_quantity, rejected_quantity, ideal_production_seconds,
        availability_pct, performance_pct, quality_pct, oee_pct, refreshed_at_utc
    )
    SELECT
        date_sk, shift_sk, plant_sk, line_sk, machine_sk,
        CASE
            WHEN scheduled_shift_seconds - planned_stop_seconds < 0 THEN 0
            ELSE scheduled_shift_seconds - planned_stop_seconds
        END AS planned_production_seconds,
        planned_stop_seconds,
        CASE WHEN run_time_seconds < 0 THEN 0 ELSE run_time_seconds END,
        downtime_seconds,
        total_quantity, good_quantity, rejected_quantity, ideal_production_seconds,
        CASE
            WHEN scheduled_shift_seconds - planned_stop_seconds <= 0 THEN NULL
            ELSE 100.0 * (
                CASE WHEN run_time_seconds < 0 THEN 0 ELSE run_time_seconds END
            ) / (scheduled_shift_seconds - planned_stop_seconds)
        END AS availability_pct,
        CASE
            WHEN run_time_seconds <= 0 THEN NULL
            ELSE 100.0 * ideal_production_seconds / run_time_seconds
        END AS performance_pct,
        CASE
            WHEN total_quantity <= 0 THEN NULL
            ELSE 100.0 * good_quantity / total_quantity
        END AS quality_pct,
        CASE
            WHEN scheduled_shift_seconds - planned_stop_seconds <= 0 OR run_time_seconds <= 0 OR total_quantity <= 0
                THEN NULL
            ELSE
                (
                    100.0 * run_time_seconds / (scheduled_shift_seconds - planned_stop_seconds)
                )
                * (
                    100.0 * ideal_production_seconds / run_time_seconds
                )
                * (
                    100.0 * good_quantity / total_quantity
                ) / 10000.0
        END AS oee_pct,
        CURRENT_TIMESTAMP
    FROM metrics;
END;
GO
