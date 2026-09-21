from __future__ import annotations

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def test_eventstream_definition_has_required_graph_components() -> None:
    topology = json.loads((ROOT / "eventstream/eventstream.json").read_text())
    assert set(("sources", "destinations", "operators", "streams")).issubset(topology)
    assert topology["sources"][0]["type"] == "CustomEndpoint"
    destination_types = {d["type"] for d in topology["destinations"]}
    assert "Eventhouse" in destination_types
    assert "Activator" in destination_types


def test_realtime_config_declares_hot_path_and_alerts() -> None:
    config = yaml.safe_load((ROOT.parent / "config/fabric_realtime.yaml").read_text())
    assert config["source"]["type"] == "CustomEndpoint"
    assert config["eventhouse"]["raw_table"] == "IndustrialIoTEvent"
    assert "MACHINE_FAULT_CRITICAL" in config["alerts"]
    assert "TELEMETRY_VIBRATION_CRITICAL" in config["alerts"]


def test_kql_pack_contains_required_realtime_functions() -> None:
    kql = (ROOT / "kql/02_realtime_queries.kql").read_text()
    for name in (
        "rt_latest_machine_telemetry",
        "rt_recent_critical_incidents",
        "rt_machine_risk",
        "rt_production_15m",
        "rt_production_losses",
        "rt_plant_realtime_kpi",
        "rt_stream_health",
    ):
        assert f"function" in kql and name in kql


def test_activator_rules_and_power_automate_contracts_are_connected() -> None:
    rules = yaml.safe_load((ROOT.parent / "config/activator_rules.yaml").read_text())
    assert len(rules["rules"]) == 6
    assert all(rule["action"]["type"] == "custom_action" for rule in rules["rules"])
    assert "IndustrialIoT_Critical_Incident_Response" in str(rules)

    flow = (ROOT / "power_automate/01_critical_incident_response.yaml").read_text()
    assert "Activator_CustomAction" in flow
    assert "IndustrialIoTIncident" in flow
    assert "MaintenanceWorkItem" in flow


def test_simulator_eventstream_bridge_is_optional_and_environment_driven() -> None:
    module = (ROOT.parent / "simulator/src/industrial_sim/transport/eventstream.py").read_text()
    cli = (ROOT.parent / "simulator/src/industrial_sim/cli/main.py").read_text()
    assert "FABRIC_EVENTSTREAM_CONNECTION_STRING" in module
    assert "FABRIC_EVENTSTREAM_FQDN" in module
    assert "--publish-eventstream" in cli
    assert "EventHubEventstreamPublisher" in cli


def test_realtime_dashboard_and_dataverse_contracts_exist() -> None:
    dashboard = yaml.safe_load((ROOT / "real_time_dashboard.yaml").read_text())
    assert len(dashboard["tiles"]) >= 6
    entities = yaml.safe_load((ROOT.parent / "config/dataverse_operational_entities.yaml").read_text())["entities"]
    assert "IndustrialIoTIncident" in entities
    assert "MaintenanceWorkItem" in entities
    assert "ProductionLossWorkItem" in entities