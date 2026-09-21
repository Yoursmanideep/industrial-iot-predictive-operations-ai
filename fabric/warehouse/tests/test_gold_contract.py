from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def test_warehouse_config_declares_star_schema_and_kpis() -> None:
    config = yaml.safe_load((ROOT / "config/fabric_warehouse.yaml").read_text())
    assert config["dimension_strategy"]["mdm_surrogate_keys_reused"] is True
    assert config["consumption"]["power_bi_surface"] == "mart"
    assert config["kpi_definitions"]["oee"] == "availability * performance * quality"


def test_gold_schema_contains_conformed_dimensions_and_facts() -> None:
    sql = (ROOT / "fabric/warehouse/001_gold_schema.sql").read_text()
    for name in (
        "gold.dim_date", "gold.dim_shift", "gold.dim_shift_calendar", "gold.dim_plant",
        "gold.dim_production_area", "gold.dim_line", "gold.dim_machine_model", "gold.dim_machine",
        "gold.dim_product", "gold.dim_operator", "gold.dim_technician", "gold.dim_supplier",
        "gold.dim_spare_part", "gold.dim_failure_mode", "gold.dim_alarm_code",
        "gold.dim_production_reason", "gold.dim_quality_defect", "gold.fact_machine_telemetry",
        "gold.fact_machine_operational_event", "gold.fact_downtime_interval", "gold.fact_production_event",
        "gold.fact_production_loss", "gold.fact_maintenance_event", "gold.fact_quality_event", "gold.fact_oee_daily"
    ):
        assert f"CREATE TABLE {name}" in sql


def test_fact_loader_supports_idempotent_merge_and_cross_window_state() -> None:
    sql = (ROOT / "fabric/warehouse/003_gold_fact_load.sql").read_text()
    assert sql.count("MERGE gold.") >= 7
    assert "LEAD(event_time_utc)" in sql
    assert "dim_shift_calendar" in sql
    assert "ranked_before_window" in sql
    assert "WHEN MATCHED THEN" in sql


def test_oee_logic_is_component_based() -> None:
    sql = (ROOT / "fabric/warehouse/003_gold_fact_load.sql").read_text()
    assert "planned_production_seconds" in sql
    assert "ideal_production_seconds" in sql
    assert "good_quantity" in sql
    assert "performance_pct" in sql
    assert "quality_pct" in sql


def test_kpi_views_reaggregate_components() -> None:
    sql = (ROOT / "fabric/warehouse/004_gold_kpi_views.sql").read_text()
    assert "SUM(f.run_time_seconds)" in sql
    assert "SUM(f.planned_production_seconds)" in sql
    assert "SUM(f.ideal_production_seconds)" in sql
    assert "SUM(f.good_quantity)" in sql


def test_orchestration_and_pipeline_are_connected() -> None:
    proc = (ROOT / "fabric/warehouse/005_gold_orchestration.sql").read_text()
    pipeline = (ROOT / "fabric/pipelines/03_silver_to_warehouse_contract.yaml").read_text()
    assert "gold.usp_load_dimensions" in proc
    assert "gold.usp_load_facts" in proc
    assert "gold.usp_refresh_oee" in proc
    assert "control.gold_load_audit" in proc
    assert "gold.usp_refresh_gold" in pipeline
    assert "Power BI" in pipeline