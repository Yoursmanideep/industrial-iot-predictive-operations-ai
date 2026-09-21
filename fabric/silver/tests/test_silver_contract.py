from __future__ import annotations

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]


def test_silver_config_declares_three_domain_tables() -> None:
    config = yaml.safe_load((ROOT / "config/fabric_silver.yaml").read_text())
    tables = config["tables"]
    assert set(tables) == {"telemetry", "operational", "production"}
    assert all(value.startswith("silver.") for value in tables.values())


def test_silver_schemas_are_strict() -> None:
    for name in (
        "machine_telemetry.schema.json",
        "machine_operational_event.schema.json",
        "production_event.schema.json",
    ):
        schema = json.loads((ROOT / "schemas/silver" / name).read_text())
        assert schema["additionalProperties"] is False
        assert "event_id" in schema["required"]
        assert "ingestion_batch_id" in schema["required"]
        assert "is_late_arrival" in schema["required"]


def test_silver_notebook_contains_fail_closed_master_validation() -> None:
    notebook = (ROOT / "fabric/notebooks/02_bronze_to_silver.py").read_text()
    assert "fail-closed" in notebook
    assert "MACHINE_MASTER_NOT_FOUND" in notebook
    assert "EVENT_ID_PAYLOAD_CONFLICT" in notebook
    assert "whenNotMatchedInsertAll" in notebook


def test_silver_sql_has_audit_and_rejection_tables() -> None:
    sql = (ROOT / "fabric/sql/002_silver_layer.sql").read_text().lower()
    assert "silver_load_audit" in sql
    assert "silver.rejected_event" in sql
    assert "event_id" in sql