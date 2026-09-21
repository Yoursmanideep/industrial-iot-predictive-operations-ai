-- Stage 3.12 — Gold orchestration procedure

DROP PROCEDURE IF EXISTS gold.usp_refresh_gold;
GO

CREATE PROCEDURE gold.usp_refresh_gold
    @gold_run_id VARCHAR(68),
    @source_window_start_utc DATETIME2(3),
    @source_window_end_utc DATETIME2(3)
AS
BEGIN
    DECLARE @started_at_utc DATETIME2(3) = CURRENT_TIMESTAMP;
    DECLARE @business_date_start DATE = CAST(DATEADD(minute, 330, @source_window_start_utc) AS DATE);
    DECLARE @business_date_end DATE = CAST(DATEADD(minute, 330, DATEADD(minute, -1, @source_window_end_utc)) AS DATE);

    EXEC gold.usp_load_dimensions
        @date_start = DATEADD(day, -1, @business_date_start),
        @date_end = DATEADD(day, 1, @business_date_end);

    EXEC gold.usp_load_facts
        @source_window_start_utc = @source_window_start_utc,
        @source_window_end_utc = @source_window_end_utc;

    EXEC gold.usp_refresh_oee
        @business_date_start = @business_date_start,
        @business_date_end = @business_date_end;

    INSERT INTO control.gold_load_audit (
        gold_run_id,
        started_at_utc,
        completed_at_utc,
        source_window_start_utc,
        source_window_end_utc,
        telemetry_rows,
        operational_rows,
        downtime_rows,
        production_rows,
        maintenance_rows,
        quality_rows,
        oee_rows,
        status,
        error_code,
        details
    )
    SELECT
        @gold_run_id,
        @started_at_utc,
        CURRENT_TIMESTAMP,
        @source_window_start_utc,
        @source_window_end_utc,
        (SELECT COUNT_BIG(*) FROM gold.fact_machine_telemetry
          WHERE event_time_utc >= @source_window_start_utc AND event_time_utc < @source_window_end_utc),
        (SELECT COUNT_BIG(*) FROM gold.fact_machine_operational_event
          WHERE event_time_utc >= @source_window_start_utc AND event_time_utc < @source_window_end_utc),
        (SELECT COUNT_BIG(*) FROM gold.fact_downtime_interval
          WHERE interval_start_utc < @source_window_end_utc AND interval_end_utc > @source_window_start_utc),
        (SELECT COUNT_BIG(*) FROM gold.fact_production_event
          WHERE event_time_utc >= @source_window_start_utc AND event_time_utc < @source_window_end_utc),
        (SELECT COUNT_BIG(*) FROM gold.fact_maintenance_event
          WHERE event_time_utc >= @source_window_start_utc AND event_time_utc < @source_window_end_utc),
        (SELECT COUNT_BIG(*) FROM gold.fact_quality_event
          WHERE event_time_utc >= @source_window_start_utc AND event_time_utc < @source_window_end_utc),
        (SELECT COUNT_BIG(*) FROM gold.fact_oee_daily
          WHERE date_sk >= YEAR(@business_date_start) * 10000 + MONTH(@business_date_start) * 100 + DAY(@business_date_start)
            AND date_sk <= YEAR(@business_date_end) * 10000 + MONTH(@business_date_end) * 100 + DAY(@business_date_end)),
        'COMPLETED',
        NULL,
        'Gold dimensions, event facts, downtime intervals, maintenance/quality facts and OEE refreshed for the requested UTC window.'
    );
END;
GO
