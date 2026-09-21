-- Stage 3.12 — SQL-first Gold star schema

CREATE SCHEMA gold;
CREATE SCHEMA mart;
CREATE SCHEMA control;

CREATE TABLE gold.dim_date (
    date_sk INT NOT NULL,
    calendar_date DATE NULL,
    calendar_year SMALLINT NULL,
    calendar_quarter TINYINT NULL,
    month_number TINYINT NULL,
    month_name VARCHAR(20) NULL,
    week_of_year TINYINT NULL,
    day_of_month TINYINT NULL,
    day_of_week_number TINYINT NULL,
    day_name VARCHAR(20) NULL,
    is_weekday BIT NULL,
    fiscal_year SMALLINT NULL,
    fiscal_quarter TINYINT NULL,
    fiscal_month_number TINYINT NULL
);

CREATE TABLE gold.dim_shift (
    shift_sk BIGINT NOT NULL,
    shift_id VARCHAR(10) NOT NULL,
    shift_name VARCHAR(80) NOT NULL,
    start_local TIME NOT NULL,
    end_local TIME NOT NULL,
    crosses_midnight BIT NOT NULL,
    status VARCHAR(20) NOT NULL
);

CREATE TABLE gold.dim_shift_calendar (
    shift_calendar_sk BIGINT IDENTITY,
    business_date_sk INT NOT NULL,
    shift_sk BIGINT NOT NULL,
    shift_start_utc DATETIME2(3) NOT NULL,
    shift_end_utc DATETIME2(3) NOT NULL
);

CREATE TABLE gold.dim_plant (
    plant_sk BIGINT NOT NULL,
    plant_id VARCHAR(20) NOT NULL,
    plant_name VARCHAR(150) NOT NULL,
    city VARCHAR(80) NOT NULL,
    state VARCHAR(80) NOT NULL,
    country VARCHAR(80) NOT NULL,
    timezone_name VARCHAR(64) NOT NULL,
    currency_code VARCHAR(3) NOT NULL,
    status VARCHAR(20) NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE NULL,
    is_current BIT NOT NULL
);

CREATE TABLE gold.dim_production_area (
    production_area_sk BIGINT NOT NULL,
    production_area_id VARCHAR(20) NOT NULL,
    plant_sk BIGINT NOT NULL,
    area_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE NULL,
    is_current BIT NOT NULL
);

CREATE TABLE gold.dim_line (
    line_sk BIGINT NOT NULL,
    line_id VARCHAR(20) NOT NULL,
    plant_sk BIGINT NOT NULL,
    production_area_sk BIGINT NOT NULL,
    line_name VARCHAR(100) NOT NULL,
    line_type VARCHAR(60) NULL,
    status VARCHAR(20) NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE NULL,
    is_current BIT NOT NULL
);

CREATE TABLE gold.dim_machine_model (
    machine_model_sk BIGINT NOT NULL,
    machine_model_code VARCHAR(40) NOT NULL,
    machine_type_code VARCHAR(40) NOT NULL,
    manufacturer_name VARCHAR(120) NOT NULL,
    model_name VARCHAR(120) NOT NULL,
    model_description VARCHAR(500) NULL,
    status VARCHAR(20) NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE NULL,
    is_current BIT NOT NULL
);

CREATE TABLE gold.dim_machine (
    machine_sk BIGINT NOT NULL,
    machine_id VARCHAR(40) NOT NULL,
    line_sk BIGINT NOT NULL,
    machine_model_sk BIGINT NOT NULL,
    machine_type_code VARCHAR(40) NOT NULL,
    machine_sequence INT NOT NULL,
    serial_number VARCHAR(80) NULL,
    installation_date DATE NULL,
    rated_capacity DECIMAL(18,4) NULL,
    capacity_uom VARCHAR(20) NULL,
    operating_temperature_min_c DECIMAL(10,3) NULL,
    operating_temperature_max_c DECIMAL(10,3) NULL,
    criticality VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE NULL,
    is_current BIT NOT NULL
);

CREATE TABLE gold.dim_product (
    product_sk BIGINT NOT NULL,
    product_id VARCHAR(40) NOT NULL,
    product_name VARCHAR(150) NOT NULL,
    product_family VARCHAR(100) NOT NULL,
    product_category VARCHAR(100) NOT NULL,
    unit_of_measure VARCHAR(20) NOT NULL,
    standard_cycle_time_seconds DECIMAL(12,3) NULL,
    standard_unit_cost_inr DECIMAL(18,2) NULL,
    status VARCHAR(20) NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE NULL,
    is_current BIT NOT NULL
);

CREATE TABLE gold.dim_failure_mode (
    failure_mode_sk BIGINT NOT NULL,
    failure_mode_code VARCHAR(50) NOT NULL,
    failure_category VARCHAR(50) NOT NULL,
    failure_name VARCHAR(150) NOT NULL,
    machine_type_code VARCHAR(40) NOT NULL,
    severity_default VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL
);

CREATE TABLE gold.dim_alarm_code (
    alarm_code_sk BIGINT NOT NULL,
    alarm_code VARCHAR(50) NOT NULL,
    alarm_name VARCHAR(150) NOT NULL,
    alarm_category VARCHAR(50) NOT NULL,
    default_severity VARCHAR(20) NOT NULL,
    machine_type_code VARCHAR(40) NOT NULL,
    trigger_signal VARCHAR(80) NOT NULL,
    status VARCHAR(20) NOT NULL
);

CREATE TABLE gold.dim_production_reason (
    reason_sk BIGINT NOT NULL,
    reason_code VARCHAR(50) NOT NULL,
    reason_name VARCHAR(150) NOT NULL,
    reason_domain VARCHAR(20) NOT NULL,
    loss_category VARCHAR(30) NULL,
    status VARCHAR(20) NOT NULL
);

CREATE TABLE gold.dim_quality_defect (
    defect_sk BIGINT NOT NULL,
    defect_code VARCHAR(50) NOT NULL,
    defect_name VARCHAR(150) NOT NULL,
    defect_category VARCHAR(50) NOT NULL,
    default_severity VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL
);

CREATE TABLE gold.fact_machine_telemetry (
    telemetry_fact_key BIGINT IDENTITY,
    event_id VARCHAR(50) NOT NULL,
    date_sk INT NOT NULL,
    shift_sk BIGINT NOT NULL,
    plant_sk BIGINT NOT NULL,
    line_sk BIGINT NOT NULL,
    machine_sk BIGINT NOT NULL,
    machine_model_sk BIGINT NULL,
    event_time_utc DATETIME2(3) NOT NULL,
    ingestion_time_utc DATETIME2(3) NOT NULL,
    operating_state VARCHAR(30) NULL,
    temperature_c DECIMAL(18,6) NULL,
    vibration_mm_s DECIMAL(18,6) NULL,
    pressure_bar DECIMAL(18,6) NULL,
    spindle_rpm DECIMAL(18,6) NULL,
    power_kw DECIMAL(18,6) NULL,
    production_rate_unit_min DECIMAL(18,6) NULL,
    quality_score_pct DECIMAL(18,6) NULL,
    feed_rate_mm_min DECIMAL(18,6) NULL,
    hydraulic_pressure_bar DECIMAL(18,6) NULL,
    force_kn DECIMAL(18,6) NULL,
    cycle_time_s DECIMAL(18,6) NULL,
    motor_temperature_c DECIMAL(18,6) NULL,
    torque_nm DECIMAL(18,6) NULL,
    position_error_mm DECIMAL(18,6) NULL,
    motor_current_a DECIMAL(18,6) NULL,
    belt_speed_m_s DECIMAL(18,6) NULL,
    discharge_pressure_bar DECIMAL(18,6) NULL,
    rpm DECIMAL(18,6) NULL,
    chamber_temperature_c DECIMAL(18,6) NULL,
    fuel_flow_rate DECIMAL(18,6) NULL,
    pressure_mbar DECIMAL(18,6) NULL,
    inspection_cycle_time_s DECIMAL(18,6) NULL,
    measurement_deviation_mm DECIMAL(18,6) NULL,
    defect_probability_pct DECIMAL(18,6) NULL,
    equipment_temperature_c DECIMAL(18,6) NULL,
    throughput_unit_min DECIMAL(18,6) NULL,
    is_late_arrival BIT NOT NULL,
    ingestion_batch_id VARCHAR(68) NOT NULL,
    simulator_run_id VARCHAR(40) NULL,
    scenario_id VARCHAR(60) NULL,
    scenario_instance_id VARCHAR(50) NULL,
    generation_sequence BIGINT NULL,
    payload_sha256 VARCHAR(64) NOT NULL
);

CREATE TABLE gold.fact_machine_operational_event (
    operational_event_fact_key BIGINT IDENTITY,
    event_id VARCHAR(50) NOT NULL,
    date_sk INT NOT NULL,
    shift_sk BIGINT NOT NULL,
    plant_sk BIGINT NOT NULL,
    line_sk BIGINT NOT NULL,
    machine_sk BIGINT NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_time_utc DATETIME2(3) NOT NULL,
    operating_state VARCHAR(30) NULL,
    previous_state VARCHAR(30) NULL,
    new_state VARCHAR(30) NULL,
    alarm_sk BIGINT NULL,
    failure_mode_sk BIGINT NULL,
    severity VARCHAR(30) NULL,
    fault_code VARCHAR(60) NULL,
    operator_id VARCHAR(40) NULL,
    work_order_id VARCHAR(60) NULL,
    is_planned BIT NULL,
    estimated_duration_seconds DECIMAL(18,3) NULL,
    communication_gap_seconds DECIMAL(18,3) NULL,
    is_late_arrival BIT NOT NULL,
    ingestion_batch_id VARCHAR(68) NOT NULL,
    simulator_run_id VARCHAR(40) NULL,
    scenario_id VARCHAR(60) NULL,
    scenario_instance_id VARCHAR(50) NULL,
    generation_sequence BIGINT NULL,
    payload_sha256 VARCHAR(64) NOT NULL
);

CREATE TABLE gold.fact_downtime_interval (
    downtime_fact_key BIGINT IDENTITY,
    start_event_id VARCHAR(50) NOT NULL,
    end_event_id VARCHAR(50) NULL,
    date_sk INT NOT NULL,
    shift_sk BIGINT NOT NULL,
    plant_sk BIGINT NOT NULL,
    line_sk BIGINT NOT NULL,
    machine_sk BIGINT NOT NULL,
    state_code VARCHAR(30) NOT NULL,
    downtime_category VARCHAR(40) NOT NULL,
    is_planned BIT NOT NULL,
    interval_start_utc DATETIME2(3) NOT NULL,
    interval_end_utc DATETIME2(3) NOT NULL,
    duration_seconds DECIMAL(18,3) NOT NULL
);

CREATE TABLE gold.fact_production_event (
    production_event_fact_key BIGINT IDENTITY,
    event_id VARCHAR(50) NOT NULL,
    date_sk INT NOT NULL,
    shift_sk BIGINT NOT NULL,
    plant_sk BIGINT NOT NULL,
    line_sk BIGINT NULL,
    machine_sk BIGINT NULL,
    product_sk BIGINT NULL,
    production_order_id VARCHAR(60) NOT NULL,
    batch_id VARCHAR(60) NULL,
    event_type VARCHAR(100) NOT NULL,
    event_time_utc DATETIME2(3) NOT NULL,
    actual_quantity DECIMAL(18,4) NULL,
    good_quantity DECIMAL(18,4) NULL,
    rejected_quantity DECIMAL(18,4) NULL,
    planned_quantity DECIMAL(18,4) NULL,
    quantity_uom VARCHAR(20) NULL,
    loss_quantity DECIMAL(18,4) NULL,
    loss_duration_seconds DECIMAL(18,3) NULL,
    loss_category VARCHAR(30) NULL,
    loss_reason_code VARCHAR(60) NULL,
    downtime_event_id VARCHAR(50) NULL,
    machine_fault_event_id VARCHAR(50) NULL,
    is_late_arrival BIT NOT NULL,
    ingestion_batch_id VARCHAR(68) NOT NULL,
    simulator_run_id VARCHAR(40) NULL,
    scenario_id VARCHAR(60) NULL,
    scenario_instance_id VARCHAR(50) NULL,
    generation_sequence BIGINT NULL,
    payload_sha256 VARCHAR(64) NOT NULL
);

CREATE TABLE gold.fact_production_loss (
    production_loss_fact_key BIGINT IDENTITY,
    event_id VARCHAR(50) NOT NULL,
    date_sk INT NOT NULL,
    shift_sk BIGINT NOT NULL,
    plant_sk BIGINT NOT NULL,
    line_sk BIGINT NULL,
    machine_sk BIGINT NULL,
    product_sk BIGINT NULL,
    loss_category VARCHAR(30) NOT NULL,
    loss_reason_code VARCHAR(60) NULL,
    loss_quantity DECIMAL(18,4) NOT NULL,
    loss_duration_seconds DECIMAL(18,3) NULL,
    event_time_utc DATETIME2(3) NOT NULL
);

CREATE TABLE gold.fact_maintenance_event (
    maintenance_event_fact_key BIGINT IDENTITY,
    event_id VARCHAR(50) NOT NULL,
    date_sk INT NOT NULL,
    shift_sk BIGINT NOT NULL,
    plant_sk BIGINT NOT NULL,
    line_sk BIGINT NULL,
    machine_sk BIGINT NULL,
    work_order_id VARCHAR(60) NULL,
    technician_id VARCHAR(40) NULL,
    event_type VARCHAR(100) NOT NULL,
    maintenance_type VARCHAR(30) NULL,
    failure_mode_sk BIGINT NULL,
    spare_part_id VARCHAR(60) NULL,
    quantity_consumed DECIMAL(18,4) NULL,
    event_time_utc DATETIME2(3) NOT NULL,
    ingestion_batch_id VARCHAR(68) NOT NULL,
    payload_sha256 VARCHAR(64) NOT NULL
);

CREATE TABLE gold.fact_quality_event (
    quality_event_fact_key BIGINT IDENTITY,
    event_id VARCHAR(50) NOT NULL,
    date_sk INT NOT NULL,
    shift_sk BIGINT NOT NULL,
    plant_sk BIGINT NOT NULL,
    line_sk BIGINT NULL,
    machine_sk BIGINT NULL,
    product_sk BIGINT NULL,
    production_order_id VARCHAR(60) NULL,
    batch_id VARCHAR(60) NULL,
    event_type VARCHAR(100) NOT NULL,
    defect_sk BIGINT NULL,
    severity VARCHAR(30) NULL,
    measurement_value DECIMAL(18,6) NULL,
    measurement_uom VARCHAR(30) NULL,
    disposition VARCHAR(30) NULL,
    event_time_utc DATETIME2(3) NOT NULL,
    ingestion_batch_id VARCHAR(68) NOT NULL,
    payload_sha256 VARCHAR(64) NOT NULL
);

CREATE TABLE gold.fact_oee_daily (
    oee_fact_key BIGINT IDENTITY,
    date_sk INT NOT NULL,
    shift_sk BIGINT NOT NULL,
    plant_sk BIGINT NOT NULL,
    line_sk BIGINT NOT NULL,
    machine_sk BIGINT NULL,
    planned_production_seconds DECIMAL(18,3) NOT NULL,
    planned_stop_seconds DECIMAL(18,3) NOT NULL,
    run_time_seconds DECIMAL(18,3) NOT NULL,
    downtime_seconds DECIMAL(18,3) NOT NULL,
    total_quantity DECIMAL(18,4) NOT NULL,
    good_quantity DECIMAL(18,4) NOT NULL,
    rejected_quantity DECIMAL(18,4) NOT NULL,
    ideal_production_seconds DECIMAL(18,3) NOT NULL,
    availability_pct DECIMAL(9,4) NULL,
    performance_pct DECIMAL(9,4) NULL,
    quality_pct DECIMAL(9,4) NULL,
    oee_pct DECIMAL(9,4) NULL,
    refreshed_at_utc DATETIME2(3) NOT NULL
);

CREATE TABLE control.gold_load_audit (
    gold_run_id VARCHAR(68) NOT NULL,
    started_at_utc DATETIME2(3) NOT NULL,
    completed_at_utc DATETIME2(3) NULL,
    source_window_start_utc DATETIME2(3) NULL,
    source_window_end_utc DATETIME2(3) NULL,
    telemetry_rows BIGINT NOT NULL,
    operational_rows BIGINT NOT NULL,
    downtime_rows BIGINT NOT NULL,
    production_rows BIGINT NOT NULL,
    maintenance_rows BIGINT NOT NULL,
    quality_rows BIGINT NOT NULL,
    oee_rows BIGINT NOT NULL,
    status VARCHAR(30) NOT NULL,
    error_code VARCHAR(100) NULL,
    details VARCHAR(4000) NULL
);
