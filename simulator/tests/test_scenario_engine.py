from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from industrial_sim.domain.scenario import ScenarioStage, ScenarioStatus
from industrial_sim.scenarios.catalog import load_scenario_catalog
from industrial_sim.scenarios.deterministic import deterministic_scenario_instance_id
from industrial_sim.scenarios.engine import ScenarioEngine

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
RUN_ID = UUID("12345678-1234-5678-1234-567812345678")
START = datetime(2026, 9, 21, 6, 0, tzinfo=timezone.utc)


def engine() -> ScenarioEngine:
    return ScenarioEngine(load_scenario_catalog(CONFIG_DIR / "scenario_catalog.yaml"))


def test_catalog_contains_all_25_scenarios() -> None:
    catalog = load_scenario_catalog(CONFIG_DIR / "scenario_catalog.yaml")
    assert len(catalog.definitions) == 25
    assert len(set(catalog.definitions)) == 25


def test_scenario_instance_id_is_deterministic() -> None:
    first = deterministic_scenario_instance_id(RUN_ID, "CHN-L01-CNC01", "SCN-CNC-BRG", START, 1)
    second = deterministic_scenario_instance_id(RUN_ID, "CHN-L01-CNC01", "SCN-CNC-BRG", START, 1)
    assert first == second


def test_duration_is_deterministic_and_within_catalog_bounds() -> None:
    catalog = load_scenario_catalog(CONFIG_DIR / "scenario_catalog.yaml")
    definition = catalog.get("SCN-CNC-BRG")
    scenario_engine = engine()
    first = scenario_engine.create_instance(RUN_ID, "CHN-L01-CNC01", "SCN-CNC-BRG", START, 1)
    second = scenario_engine.create_instance(RUN_ID, "CHN-L01-CNC01", "SCN-CNC-BRG", START, 1)
    duration_minutes = (first.planned_end_at - START).total_seconds() / 60
    assert first.scenario_instance_id == second.scenario_instance_id
    assert definition.progression_min_minutes <= duration_minutes <= definition.progression_max_minutes


def test_progression_reaches_expected_stages() -> None:
    scenario_engine = engine()
    instance = scenario_engine.create_instance(RUN_ID, "CHN-L01-CNC01", "SCN-CNC-BRG", START, 1)
    total = instance.duration_seconds()

    early, _ = scenario_engine.advance(instance, START + timedelta(seconds=total * 0.10))
    anomaly, _ = scenario_engine.advance(instance, START + timedelta(seconds=total * 0.40))
    critical, _ = scenario_engine.advance(instance, START + timedelta(seconds=total * 0.65))
    failure, _ = scenario_engine.advance(instance, instance.planned_end_at)

    assert early.stage is ScenarioStage.EARLY_DEGRADATION
    assert anomaly.stage is ScenarioStage.ANOMALY
    assert critical.stage is ScenarioStage.CRITICAL
    assert failure.stage is ScenarioStage.FAILURE
    assert instance.status is ScenarioStatus.FAILED


def test_predictive_intervention_avoids_failure() -> None:
    scenario_engine = engine()
    instance = scenario_engine.create_instance(RUN_ID, "CHN-L01-CNC01", "SCN-CNC-BRG", START, 1)
    scenario_engine.advance(instance, START + timedelta(seconds=instance.duration_seconds() * 0.30))

    transition = scenario_engine.intervene(instance, START + timedelta(minutes=20), "EVT-12345678-1234-5678-1234-567812345678")

    assert transition is not None
    assert instance.stage is ScenarioStage.MAINTENANCE
    assert instance.status is ScenarioStatus.AVOIDED
    assert instance.intervention_event_id is not None


def test_failure_path_supports_maintenance_and_recovery() -> None:
    scenario_engine = engine()
    instance = scenario_engine.create_instance(RUN_ID, "CHN-L01-CNC01", "SCN-CNC-BRG", START, 1)
    scenario_engine.advance(instance, instance.planned_end_at)
    assert instance.stage is ScenarioStage.FAILURE

    # Corrective workflow moves the scenario through maintenance and recovery.
    instance.stage = ScenarioStage.MAINTENANCE
    maintenance = scenario_engine.complete_maintenance(instance, instance.planned_end_at + timedelta(minutes=30))
    recovery = scenario_engine.complete_recovery(instance, instance.planned_end_at + timedelta(minutes=45))

    assert maintenance.to_stage is ScenarioStage.RECOVERY
    assert recovery.to_stage is ScenarioStage.BASELINE
    assert instance.status is ScenarioStatus.RESOLVED
