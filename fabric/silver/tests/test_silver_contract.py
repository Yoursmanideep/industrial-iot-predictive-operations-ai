from __future__ import annotations

import ast
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]


def test_silver_config_declares_three_domain_tables_and_mdm() -> None:
    config = yaml.safe_load((ROOT / "config/fabric_silver.yaml").read_text())
    tables = config["tables"]
    assert set(tables) == {"telemetry", "operational", "production"}
    assert all(value.startswith("silver.") for value in tables.values())
    assert config["master_data"]["plant_table"] == "mdm.dim_plant"


def test_silver_schemas_are_strict_and_lineage_preserving() -> None:
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
        assert "event_payload_json" in schema["properties"]


def test_silver_notebook_is_valid_python_syntax() -> None:
    source = (ROOT / "fabric/notebooks/02_bronze_to_silver.py").read_text()
    ast.parse(source)


def test_silver_notebook_contains_required_quality_controls() -> None:
    notebook = (ROOT / "fabric/notebooks/02_bronze_to_silver.py").read_text()
    assert 'Window.partitionBy("ingestion_batch_id")' in notebook
    assert "fail-closed" in notebook
    assert "PLANT_MASTER_NOT_FOUND" in notebook
    assert "MACHINE_TYPE_MISMATCH" in notebook
    assert "EVENT_ID_PAYLOAD_CONFLICT" in notebook
    assert "whenNotMatchedInsertAll" in notebook
    assert "whenMatchedUpdateAll" in notebook


def test_silver_sql_has_audit_and_rejection_tables() -> None:
    sql = (ROOT / "fabric/sql/002_silver_layer.sql").read_text().lower()
    assert "control.silver_load_audit" in sql
    assert "silver.rejected_event" in sql
    assert "event_id" in sql
