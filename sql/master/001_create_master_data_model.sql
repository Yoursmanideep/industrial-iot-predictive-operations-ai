-- Stage 3.1 — Physical Master Data Model
-- Industrial IoT Predictive Operations & AI Intelligence Platform

-- Design notes:
-- 1. *_sk columns are warehouse surrogate keys.
-- 2. *_id / *_code columns are immutable business/reference keys.
-- 3. Historical dimensions use effective_from, effective_to and is_current.
-- 4. Referential integrity is validated by load/data-quality processes.
-- 5. Do not treat GitHub configuration as production master data.

-- ===========================
-- MDM / ORGANIZATION
-- ===========================

CREATE SCHEMA mdm;

CREATE TABLE mdm.dim_plant (
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
    is_current BOOLEAN NOT NULL
);

CREATE TABLE mdm.dim_production_area (
    production_area_sk BIGINT NOT NULL,
    production_area_id VARCHAR(20) NOT NULL,
    plant_sk BIGINT NOT NULL,
    area_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE NULL,
    is_current BOOLEAN NOT NULL
);

CREATE TABLE mdm.dim_line (
    line_sk BIGINT NOT NULL,
    line_id VARCHAR(20) NOT NULL,
    plant_sk BIGINT NOT NULL,
    production_area_sk BIGINT NOT NULL,
    line_name VARCHAR(100) NOT NULL,
    line_type VARCHAR(60) NULL,
    status VARCHAR(20) NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE NULL,
    is_current BOOLEAN NOT NULL
);

-- ===========================
-- ASSET MASTER
-- ===========================

CREATE TABLE mdm.dim_machine_model (
    machine_model_sk BIGINT NOT NULL,
    machine_model_code VARCHAR(40) NOT NULL,
    machine_type_code VARCHAR(40) NOT NULL,
    manufacturer_name VARCHAR(120) NOT NULL,
    model_name VARCHAR(120) NOT NULL,
    model_description VARCHAR(500) NULL,
    status VARCHAR(20) NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE NULL,
    is_current BOOLEAN NOT NULL
);

CREATE TABLE mdm.dim_machine (
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
    is_current BOOLEAN NOT NULL
);

-- ===========================
-- COMMERCIAL / PRODUCTION MASTER
-- ===========================

CREATE TABLE mdm.dim_product (
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
    is_current BOOLEAN NOT NULL
);

CREATE TABLE mdm.dim_shift (
    shift_sk BIGINT NOT NULL,
    shift_id VARCHAR(10) NOT NULL,
    shift_name VARCHAR(80) NOT NULL,
    start_local TIME NOT NULL,
    end_local TIME NOT NULL,
    crosses_midnight BOOLEAN NOT NULL,
    status VARCHAR(20) NOT NULL
);

-- ===========================
-- PEOPLE MASTER
-- ===========================

CREATE TABLE mdm.dim_operator (
    operator_sk BIGINT NOT NULL,
    operator_id VARCHAR(30) NOT NULL,
    operator_name VARCHAR(150) NOT NULL,
    plant_sk BIGINT NOT NULL,
    team_code VARCHAR(30) NOT NULL,
    skill_level VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE NULL,
    is_current BOOLEAN NOT NULL
);

CREATE TABLE mdm.dim_technician (
    technician_sk BIGINT NOT NULL,
    technician_id VARCHAR(30) NOT NULL,
    technician_name VARCHAR(150) NOT NULL,
    plant_sk BIGINT NOT NULL,
    specialization VARCHAR(100) NOT NULL,
    skill_level VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE NULL,
    is_current BOOLEAN NOT NULL
);

-- ===========================
-- SUPPLIER / PARTS MASTER
-- ===========================

CREATE TABLE mdm.dim_supplier (
    supplier_sk BIGINT NOT NULL,
    supplier_id VARCHAR(30) NOT NULL,
    supplier_name VARCHAR(150) NOT NULL,
    supplier_type VARCHAR(50) NOT NULL,
    country VARCHAR(80) NOT NULL,
    lead_time_days INT NOT NULL,
    status VARCHAR(20) NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE NULL,
    is_current BOOLEAN NOT NULL
);

CREATE TABLE mdm.dim_spare_part (
    spare_part_sk BIGINT NOT NULL,
    part_id VARCHAR(40) NOT NULL,
    part_name VARCHAR(150) NOT NULL,
    part_category VARCHAR(100) NOT NULL,
    part_uom VARCHAR(20) NOT NULL,
    standard_unit_cost_inr DECIMAL(18,2) NOT NULL,
    minimum_stock_quantity DECIMAL(18,4) NOT NULL,
    reorder_quantity DECIMAL(18,4) NOT NULL,
    primary_supplier_sk BIGINT NOT NULL,
    status VARCHAR(20) NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE NULL,
    is_current BOOLEAN NOT NULL
);

-- ===========================
-- GOVERNED REFERENCE TABLES
-- ===========================

CREATE SCHEMA ref;

CREATE TABLE ref.failure_mode (
    failure_mode_sk BIGINT NOT NULL,
    failure_mode_code VARCHAR(50) NOT NULL,
    failure_category VARCHAR(50) NOT NULL,
    failure_name VARCHAR(150) NOT NULL,
    machine_type_code VARCHAR(40) NOT NULL,
    severity_default VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL
);

CREATE TABLE ref.alarm_code (
    alarm_code_sk BIGINT NOT NULL,
    alarm_code VARCHAR(50) NOT NULL,
    alarm_name VARCHAR(150) NOT NULL,
    alarm_category VARCHAR(50) NOT NULL,
    default_severity VARCHAR(20) NOT NULL,
    machine_type_code VARCHAR(40) NOT NULL,
    trigger_signal VARCHAR(80) NOT NULL,
    status VARCHAR(20) NOT NULL
);

CREATE TABLE ref.production_reason (
    reason_sk BIGINT NOT NULL,
    reason_code VARCHAR(50) NOT NULL,
    reason_name VARCHAR(150) NOT NULL,
    reason_domain VARCHAR(20) NOT NULL,
    loss_category VARCHAR(30) NULL,
    status VARCHAR(20) NOT NULL
);

CREATE TABLE ref.quality_defect (
    defect_sk BIGINT NOT NULL,
    defect_code VARCHAR(50) NOT NULL,
    defect_name VARCHAR(150) NOT NULL,
    defect_category VARCHAR(50) NOT NULL,
    default_severity VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL
);

-- ===========================
-- OPERATIONAL DATA-QUALITY AUDIT
-- ===========================

CREATE SCHEMA audit;

CREATE TABLE audit.master_data_quality_result (
    quality_run_id VARCHAR(40) NOT NULL,
    run_timestamp_utc DATETIME2(3) NOT NULL,
    entity_name VARCHAR(100) NOT NULL,
    check_name VARCHAR(100) NOT NULL,
    check_status VARCHAR(20) NOT NULL,
    failed_record_count BIGINT NOT NULL,
    warning_record_count BIGINT NOT NULL,
    details VARCHAR(2000) NULL
);