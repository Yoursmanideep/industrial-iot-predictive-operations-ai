from industrial_sim.machines.profiles import load_machine_profiles
from industrial_sim.machines.registry import MachineBehaviorRegistry


def test_loads_all_nine_machine_profiles() -> None:
    catalog = load_machine_profiles("../../config/simulator_machine_profiles.yaml")
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
