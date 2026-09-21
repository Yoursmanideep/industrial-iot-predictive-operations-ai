import json
from pathlib import Path

import yaml

from industrial_sim.machines.profiles import load_machine_profiles
from industrial_sim.machines.registry import MachineBehaviorRegistry


def test_loads_all_nine_machine_profiles() -> None:
    catalog = load_machine_profiles(CONFIG_DIR / "simulator_machine_profiles.yaml")
    expected = {
        "CNC", "HYDRAULIC_PRESS", "INDUSTRIAL_ROBOT", "CONVEYOR", "COMPRESSOR",
        "FURNACE", "INSPECTION", "PACKAGING", "PALLETIZER",
    }
    assert set(catalog.profiles) == expected


def test_registry_creates_behavior_for_every_profile() -> None:
    catalog = load_machine_profiles("../../config/simulator_machine_profiles.yaml")
    registry = MachineBehaviorRegistry.with_generic_profiles(catalog)
    for machine_type in catalog.profiles:
        assert registry.get(machine_type).machine_type == machine_type


def test_profile_signals_match_stage_2_2_catalog() -> None:
    profile_path = Path("../../config/simulator_machine_profiles.yaml")
    catalog_path = Path("../../config/machine_catalog.yaml")
    profiles = yaml.safe_load(profile_path.read_text(encoding="utf-8"))["profiles"]
    catalog = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))["machine_types"]
    telemetry_schema = json.loads(schema_path.read_text(encoding="utf-8"))["properties"]

    assert set(profiles) == set(catalog)

    for machine_type, profile in profiles.items():
        assert set(profile["telemetry_signals"]) == set(catalog[machine_type]["telemetry"])
        assert set(profile["telemetry_signals"]).issubset(telemetry_schema)
