from __future__ import annotations

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "ApexIndustrialIoT.SemanticModel" / "definition"


def test_definition_pbism_is_tmdl_model() -> None:
    pbism = json.loads((ROOT / "ApexIndustrialIoT.SemanticModel" / "definition.pbism").read_text())
    assert pbism["version"].startswith("4.")


def test_required_definition_parts_exist() -> None:
    assert (MODEL / "database.tmdl").is_file()
    assert (MODEL / "model.tmdl").is_file()
    assert (MODEL / "relationships.tmdl").is_file()
    assert (MODEL / "expressions.tmdl").is_file()
    assert (MODEL / "roles" / "Plant RLS.tmdl").is_file()


def test_direct_lake_source_and_model_references_exist() -> None:
    expression = (MODEL / "expressions.tmdl").read_text()
    model = (MODEL / "model.tmdl").read_text()
    assert "AzureStorage.DataLake" in expression
    for table in ("Date", "Shift", "Plant", "Line", "Machine", "Product", "OEE", "Production", "Downtime", "Telemetry", "OperationalEvent", "PlantAccess"):
        assert f"ref table {table}" in model


def test_tmdl_tables_use_direct_lake_entity_partitions() -> None:
    table_dir = MODEL / "tables"
    required = {"Date", "Shift", "Plant", "Line", "Machine", "Product", "OEE", "Production", "Downtime", "Telemetry", "OperationalEvent", "PlantAccess"}
    actual = {p.stem for p in table_dir.glob("*.tmdl")}
    assert required.issubset(actual)
    for name in required:
        text = (table_dir / f"{name}.tmdl").read_text()
        assert "mode: directLake" in text
        assert "expressionSource: DL_Warehouse" in text
        assert "sourceColumn:" in text


def test_relationships_are_single_direction_and_dimension_driven() -> None:
    rel = (MODEL / "relationships.tmdl").read_text()
    assert "fromColumn: OEE.plant_sk" in rel
    assert "toColumn: Plant.plant_sk" in rel
    assert "fromColumn: Production.product_sk" in rel
    assert "toColumn: Product.product_sk" in rel
    assert "Shift Calendar" not in rel


def test_rls_role_uses_userprincipalname() -> None:
    role = (MODEL / "roles" / "Plant RLS.tmdl").read_text()
    assert "USERPRINCIPALNAME()" in role
    assert "PlantAccess[plant_id]" in role
    assert "Plant[plant_id] IN AllowedPlants" in role


def test_core_kpi_measures_are_present() -> None:
    oee = (MODEL / "tables" / "OEE.tmdl").read_text()
    for measure in ("Availability %", "Performance %", "Quality %", "OEE %", "Good Units", "Rejected Units"):
        assert f"measure '{measure}'" in oee


def test_model_config_and_deployment_contract_are_consistent() -> None:
    config = yaml.safe_load((ROOT.parent / "config/powerbi_semantic_model.yaml").read_text())
    deploy = yaml.safe_load((ROOT / "deployment/semantic_model_deployment.yaml").read_text())
    assert config["semantic_model"]["definition_format"] == "TMDL"
    assert config["semantic_model"]["storage_mode"] == "DirectLake"
    assert deploy["item"]["type"] == "SemanticModel"
    assert deploy["item"]["format"] == "TMDL"