-- Stage 3.12 — Gold dimension loading

DROP PROCEDURE IF EXISTS gold.usp_load_date_dimension;
GO

CREATE PROCEDURE gold.usp_load_date_dimension
    @start_date DATE,
    @end_date DATE
AS
BEGIN
    INSERT INTO gold.dim_date (
        date_sk, calendar_date, calendar_year, calendar_quarter, month_number, month_name,
        week_of_year, day_of_month, day_of_week_number, day_name, is_weekday,
        fiscal_year, fiscal_quarter, fiscal_month_number
    )
    SELECT
        YEAR(d.calendar_date) * 10000 + MONTH(d.calendar_date) * 100 + DAY(d.calendar_date),
        d.calendar_date,
        YEAR(d.calendar_date),
        DATEPART(quarter, d.calendar_date),
        MONTH(d.calendar_date),
        DATENAME(month, d.calendar_date),
        DATEPART(isowk, d.calendar_date),
        DAY(d.calendar_date),
        (DATEDIFF(day, CAST('1900-01-01' AS DATE), d.calendar_date) % 7) + 1,
        CASE (DATEDIFF(day, CAST('1900-01-01' AS DATE), d.calendar_date) % 7) + 1
            WHEN 1 THEN 'Monday'
            WHEN 2 THEN 'Tuesday'
            WHEN 3 THEN 'Wednesday'
            WHEN 4 THEN 'Thursday'
            WHEN 5 THEN 'Friday'
            WHEN 6 THEN 'Saturday'
            ELSE 'Sunday'
        END,
        CASE
            WHEN (DATEDIFF(day, CAST('1900-01-01' AS DATE), d.calendar_date) % 7) + 1 IN (6,7)
            THEN CAST(0 AS BIT) ELSE CAST(1 AS BIT)
        END,
        CASE WHEN MONTH(d.calendar_date) >= 4 THEN YEAR(d.calendar_date) + 1 ELSE YEAR(d.calendar_date) END,
        (((CASE WHEN MONTH(d.calendar_date) >= 4 THEN MONTH(d.calendar_date) - 3 ELSE MONTH(d.calendar_date) + 9 END) - 1) / 3) + 1,
        CASE WHEN MONTH(d.calendar_date) >= 4 THEN MONTH(d.calendar_date) - 3 ELSE MONTH(d.calendar_date) + 9 END
    FROM (
        SELECT CAST(DATEADD(day, value, @start_date) AS DATE) AS calendar_date
        FROM GENERATE_SERIES(0, DATEDIFF(day, @start_date, @end_date))
    ) d
    WHERE NOT EXISTS (
        SELECT 1
        FROM gold.dim_date x
        WHERE x.date_sk = YEAR(d.calendar_date) * 10000 + MONTH(d.calendar_date) * 100 + DAY(d.calendar_date)
    );

    IF NOT EXISTS (SELECT 1 FROM gold.dim_date WHERE date_sk = 0)
    BEGIN
        INSERT INTO gold.dim_date (
            date_sk, calendar_date, calendar_year, calendar_quarter, month_number, month_name,
            week_of_year, day_of_month, day_of_week_number, day_name, is_weekday,
            fiscal_year, fiscal_quarter, fiscal_month_number
        )
        VALUES (0, NULL, NULL, NULL, NULL, 'UNKNOWN', NULL, NULL, NULL, 'UNKNOWN', NULL, NULL, NULL, NULL);
    END
END;
GO

DROP PROCEDURE IF EXISTS gold.usp_load_dimensions;
GO

CREATE PROCEDURE gold.usp_load_dimensions
    @date_start DATE,
    @date_end DATE
AS
BEGIN
    EXEC gold.usp_load_date_dimension @date_start = @date_start, @end_date = @date_end;

    TRUNCATE TABLE gold.dim_shift_calendar;

    TRUNCATE TABLE gold.dim_shift;
    INSERT INTO gold.dim_shift (
        shift_sk, shift_id, shift_name, start_local, end_local, crosses_midnight, status
    )
    SELECT shift_sk, shift_id, shift_name, start_local, end_local, crosses_midnight, status
    FROM mdm.dim_shift;

    INSERT INTO gold.dim_shift (
        shift_sk, shift_id, shift_name, start_local, end_local, crosses_midnight, status
    )
    SELECT 0, 'UNKNOWN', 'Unknown Shift', CAST('00:00:00' AS TIME), CAST('00:00:00' AS TIME), CAST(0 AS BIT), 'INACTIVE'
    WHERE NOT EXISTS (SELECT 1 FROM gold.dim_shift WHERE shift_sk = 0);

    INSERT INTO gold.dim_shift_calendar (
        business_date_sk, shift_sk, shift_start_utc, shift_end_utc
    )
    SELECT
        d.date_sk,
        s.shift_sk,
        DATEADD(
            minute,
            (DATEPART(hour, s.start_local) * 60 + DATEPART(minute, s.start_local)) - 330,
            CAST(d.calendar_date AS DATETIME2(3))
        ),
        DATEADD(
            minute,
            (DATEPART(hour, s.end_local) * 60 + DATEPART(minute, s.end_local))
                + CASE WHEN s.crosses_midnight = 1 THEN 1440 ELSE 0 END
                - 330,
            CAST(d.calendar_date AS DATETIME2(3))
        )
    FROM gold.dim_date d
    CROSS JOIN gold.dim_shift s
    WHERE d.date_sk <> 0
      AND s.shift_id IN ('SH1', 'SH2', 'SH3');

    TRUNCATE TABLE gold.dim_plant;
    INSERT INTO gold.dim_plant
    SELECT * FROM mdm.dim_plant;
    INSERT INTO gold.dim_plant (
        plant_sk, plant_id, plant_name, city, state, country, timezone_name, currency_code,
        status, effective_from, effective_to, is_current
    )
    SELECT 0, 'UNKNOWN', 'Unknown Plant', 'UNKNOWN', 'UNKNOWN', 'UNKNOWN', 'Asia/Kolkata', 'INR',
           'INACTIVE', CAST('1900-01-01' AS DATE), NULL, CAST(1 AS BIT)
    WHERE NOT EXISTS (SELECT 1 FROM gold.dim_plant WHERE plant_sk = 0);

    TRUNCATE TABLE gold.dim_production_area;
    INSERT INTO gold.dim_production_area
    SELECT * FROM mdm.dim_production_area;
    INSERT INTO gold.dim_production_area
    SELECT 0, 'UNKNOWN', 0, 'Unknown Area', 'INACTIVE', CAST('1900-01-01' AS DATE), NULL, CAST(1 AS BIT)
    WHERE NOT EXISTS (SELECT 1 FROM gold.dim_production_area WHERE production_area_sk = 0);

    TRUNCATE TABLE gold.dim_line;
    INSERT INTO gold.dim_line
    SELECT * FROM mdm.dim_line;
    INSERT INTO gold.dim_line
    SELECT 0, 'UNKNOWN', 0, 0, 'Unknown Line', 'UNKNOWN', 'INACTIVE', CAST('1900-01-01' AS DATE), NULL, CAST(1 AS BIT)
    WHERE NOT EXISTS (SELECT 1 FROM gold.dim_line WHERE line_sk = 0);

    TRUNCATE TABLE gold.dim_machine_model;
    INSERT INTO gold.dim_machine_model
    SELECT * FROM mdm.dim_machine_model;
    INSERT INTO gold.dim_machine_model
    SELECT 0, 'UNKNOWN', 'UNKNOWN', 'UNKNOWN', 'Unknown Model', 'Unknown machine model',
           'INACTIVE', CAST('1900-01-01' AS DATE), NULL, CAST(1 AS BIT)
    WHERE NOT EXISTS (SELECT 1 FROM gold.dim_machine_model WHERE machine_model_sk = 0);

    TRUNCATE TABLE gold.dim_machine;
    INSERT INTO gold.dim_machine (
        machine_sk, machine_id, line_sk, machine_model_sk, machine_type_code, machine_sequence,
        serial_number, installation_date, rated_capacity, capacity_uom,
        operating_temperature_min_c, operating_temperature_max_c, criticality, status,
        effective_from, effective_to, is_current
    )
    SELECT
        m.machine_sk, m.machine_id, m.line_sk, m.machine_model_sk, m.machine_type_code, m.machine_sequence,
        m.serial_number, m.installation_date, m.rated_capacity, m.capacity_uom,
        m.operating_temperature_min_c, m.operating_temperature_max_c, m.criticality, m.status,
        m.effective_from, m.effective_to, m.is_current
    FROM mdm.dim_machine m;
    INSERT INTO gold.dim_machine (
        machine_sk, machine_id, line_sk, machine_model_sk, machine_type_code, machine_sequence,
        serial_number, installation_date, rated_capacity, capacity_uom,
        operating_temperature_min_c, operating_temperature_max_c, criticality, status,
        effective_from, effective_to, is_current
    )
    SELECT 0, 'UNKNOWN', 0, 0, 'UNKNOWN', 0, NULL, NULL, NULL, NULL, NULL, NULL,
           'UNKNOWN', 'INACTIVE', CAST('1900-01-01' AS DATE), NULL, CAST(1 AS BIT)
    WHERE NOT EXISTS (SELECT 1 FROM gold.dim_machine WHERE machine_sk = 0);

    TRUNCATE TABLE gold.dim_product;
    INSERT INTO gold.dim_product
    SELECT * FROM mdm.dim_product;
    INSERT INTO gold.dim_product
    SELECT 0, 'UNKNOWN', 'Unknown Product', 'UNKNOWN', 'UNKNOWN', 'unit', NULL, NULL,
           'INACTIVE', CAST('1900-01-01' AS DATE), NULL, CAST(1 AS BIT)
    WHERE NOT EXISTS (SELECT 1 FROM gold.dim_product WHERE product_sk = 0);

    TRUNCATE TABLE gold.dim_operator;
    INSERT INTO gold.dim_operator
    SELECT * FROM mdm.dim_operator;
    INSERT INTO gold.dim_operator
    SELECT 0, 'UNKNOWN', 'Unknown Operator', 0, 'UNKNOWN', 'UNKNOWN', 'INACTIVE',
           CAST('1900-01-01' AS DATE), NULL, CAST(1 AS BIT)
    WHERE NOT EXISTS (SELECT 1 FROM gold.dim_operator WHERE operator_sk = 0);

    TRUNCATE TABLE gold.dim_technician;
    INSERT INTO gold.dim_technician
    SELECT * FROM mdm.dim_technician;
    INSERT INTO gold.dim_technician
    SELECT 0, 'UNKNOWN', 'Unknown Technician', 0, 'UNKNOWN', 'UNKNOWN', 'INACTIVE',
           CAST('1900-01-01' AS DATE), NULL, CAST(1 AS BIT)
    WHERE NOT EXISTS (SELECT 1 FROM gold.dim_technician WHERE technician_sk = 0);

    TRUNCATE TABLE gold.dim_supplier;
    INSERT INTO gold.dim_supplier
    SELECT * FROM mdm.dim_supplier;
    INSERT INTO gold.dim_supplier
    SELECT 0, 'UNKNOWN', 'Unknown Supplier', 'UNKNOWN', 'UNKNOWN', 0, 'INACTIVE',
           CAST('1900-01-01' AS DATE), NULL, CAST(1 AS BIT)
    WHERE NOT EXISTS (SELECT 1 FROM gold.dim_supplier WHERE supplier_sk = 0);

    TRUNCATE TABLE gold.dim_spare_part;
    INSERT INTO gold.dim_spare_part
    SELECT * FROM mdm.dim_spare_part;
    INSERT INTO gold.dim_spare_part
    SELECT 0, 'UNKNOWN', 'Unknown Part', 'UNKNOWN', 'unit', 0, 0, 0, 0, 'INACTIVE',
           CAST('1900-01-01' AS DATE), NULL, CAST(1 AS BIT)
    WHERE NOT EXISTS (SELECT 1 FROM gold.dim_spare_part WHERE spare_part_sk = 0);

    TRUNCATE TABLE gold.dim_failure_mode;
    INSERT INTO gold.dim_failure_mode
    SELECT * FROM ref.failure_mode;
    INSERT INTO gold.dim_failure_mode
    SELECT 0, 'UNKNOWN', 'UNKNOWN', 'Unknown Failure Mode', 'UNKNOWN', 'UNKNOWN', 'INACTIVE'
    WHERE NOT EXISTS (SELECT 1 FROM gold.dim_failure_mode WHERE failure_mode_sk = 0);

    TRUNCATE TABLE gold.dim_alarm_code;
    INSERT INTO gold.dim_alarm_code
    SELECT * FROM ref.alarm_code;
    INSERT INTO gold.dim_alarm_code
    SELECT 0, 'UNKNOWN', 'Unknown Alarm', 'UNKNOWN', 'UNKNOWN', 'UNKNOWN', 'UNKNOWN', 'INACTIVE'
    WHERE NOT EXISTS (SELECT 1 FROM gold.dim_alarm_code WHERE alarm_code_sk = 0);

    TRUNCATE TABLE gold.dim_production_reason;
    INSERT INTO gold.dim_production_reason
    SELECT * FROM ref.production_reason;
    INSERT INTO gold.dim_production_reason
    SELECT 0, 'UNKNOWN', 'Unknown Reason', 'UNKNOWN', NULL, 'INACTIVE'
    WHERE NOT EXISTS (SELECT 1 FROM gold.dim_production_reason WHERE reason_sk = 0);

    TRUNCATE TABLE gold.dim_quality_defect;
    INSERT INTO gold.dim_quality_defect
    SELECT * FROM ref.quality_defect;
    INSERT INTO gold.dim_quality_defect
    SELECT 0, 'UNKNOWN', 'Unknown Defect', 'UNKNOWN', 'UNKNOWN', 'INACTIVE'
    WHERE NOT EXISTS (SELECT 1 FROM gold.dim_quality_defect WHERE defect_sk = 0);
END;
GO
