from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from industrial_sim.domain.machine import Machine, MachineIdentity, MachineState
from industrial_sim.events.operational import OperationalEventFactory
from industrial_sim.scenarios.catalog import load_scenario_catalog
from industrial_sim.scenarios.engine import ScenarioEngine
from industrial_sim.scenarios.event_engine import ScenarioOperationalEventEngine

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
RUN_ID = UUID("12345678-1234-5678-1234-567812345678")
START = datetime(2026, 9, 21, 6, 0, tzinfo=timezone.utc)


def build_machine() -> Machine:
    return Machine(
        identity=MachineIdentity(
            machine_id="CHN-L01-CNC01",
            plant_id="PLT-CHN-01",
            line_id="CHN-L01",
            machine_type="CNC",
        ),
        state=MachineState.RUNNING,
    )


def test_operational_failure_chain_preserves_causation() -> None:
    catalog = load_scenario_catalog(CONFIG_DIR / "scenario_catalog.yaml")
    scenario_engine = ScenarioEngine(catalog)
    instance = scenario_engine.create_instance(
        RUN_ID, "CHN-L01-CNC01", "SCN-CNC-BRG", START, 1
    )
    definition = catalog.get("SCN-CNC-BRG")
    event_engine = ScenarioOperationalEventEngine.from_config(
        RUN_ID,
        deterministic_seed=20260921,
        configuration_version="1.0.0",
        mapping_path=CONFIG_DIR / "simulator_alarm_mapping.yaml",
        event_factory=OperationalEventFactory(),
    )

    anomaly, anomaly_transition = scenario_engine.advance(
        instance,
        START + timedelta(seconds=instance.duration_seconds() * 0.40),
    )
    assert anomaly_transition is not None
    alarm_events = event_engine.transition_events(
        build_machine(),
        anomaly_transition,
        definition.scenario_id,
        str(instance.scenario_instance_id),
        definition.failure_mode_code,
        definition.affected_signals,
        instance.correlation_id,
        1,
        "RUNNING",
    )
    assert alarm_events[0].event_type == "AlarmRaised"
    assert alarm_events[0].severity == "MEDIUM"

    failure, failure_transition = scenario_engine.advance(instance, instance.planned_end_at)
    assert failure.stage.value == "FAILURE"
    assert failure_transition is not None
    failure_events = event_engine.transition_events(
        build_machine(),
        failure_transition,
        definition.scenario_id,
        str(instance.scenario_instance_id),
        definition.failure_mode_code,
        definition.affected_signals,
        instance.correlation_id,
        2,
        "RUNNING",
    )

    assert [event.event_type for event in failure_events] == [
        "MachineFaulted",
        "StateChanged",
    ]
    assert failure_events[0].causation_id == alarm_events[0].event_id
    assert failure_events[1].causation_id == failure_events[0].event_id
    assert failure_events[1].previous_state == "RUNNING"
    assert failure_events[1].new_state == "FAULT"


def test_avoided_failure_generates_maintenance_events() -> None:
    catalog = load_scenario_catalog(CONFIG_DIR / "scenario_catalog.yaml")
    scenario_engine = ScenarioEngine(catalog)
    instance = scenario_engine.create_instance(
        RUN_ID, "CHN-L01-CNC01", "SCN-CNC-BRG", START, 10
    )
    definition = catalog.get("SCN-CNC-BRG")
    event_engine = ScenarioOperationalEventEngine.from_config(
        RUN_ID,
        deterministic_seed=20260921,
        configuration_version="1.0.0",
        mapping_path=CONFIG_DIR / "simulator_alarm_mapping.yaml",
    )

    _, anomaly_transition = scenario_engine.advance(
        instance,
        START + timedelta(seconds=instance.duration_seconds() * 0.40),
    )
    assert anomaly_transition is not None
    alarm = event_engine.transition_events(
        build_machine(),
        anomaly_transition,
        definition.scenario_id,
        str(instance.scenario_instance_id),
        definition.failure_mode_code,
        definition.affected_signals,
        instance.correlation_id,
        10,
        "RUNNING",
    )[0]

    intervention_transition = scenario_engine.intervene(
        instance,
        START + timedelta(minutes=20),
        "EVT-12345678-1234-5678-1234-567812345678",
    )
    assert intervention_transition is not None
    maintenance_events = event_engine.transition_events(
        build_machine(),
        intervention_transition,
        definition.scenario_id,
        str(instance.scenario_instance_id),
        definition.failure_mode_code,
        definition.affected_signals,
        instance.correlation_id,
        11,
        "RUNNING",
        intervention_event_id=instance.intervention_event_id,
    )

    assert [event.event_type for event in maintenance_events] == [
        "AlarmCleared",
        "MachineStopped",
    ]
    assert maintenance_events[0].causation_id == instance.intervention_event_id
    assert maintenance_events[1].causation_id == maintenance_events[0].event_id
    assert alarm.event_id != maintenance_events[0].event_id


def test_event_ids_are_reproducible_for_same_inputs() -> None:
    machine = build_machine()
    factory = OperationalEventFactory()
    first = factory.build(
        RUN_ID,
        machine,
        "AlarmRaised",
        START,
        1,
        20260921,
        "1.0.0",
        scenario_id="SCN-CNC-BRG",
        scenario_instance_id=str(UUID("12345678-1234-5678-1234-567812345678")),
        alarm_code="VIBRATION_HIGH",
        alarm_name="Vibration High",
        severity="MEDIUM",
        operating_state="RUNNING",
    )
    second = factory.build(
        RUN_ID,
        machine,
        "AlarmRaised",
        START,
        1,
        20260921,
        "1.0.0",
        scenario_id="SCN-CNC-BRG",
        scenario_instance_id=str(UUID("12345678-1234-5678-1234-567812345678")),
        alarm_code="VIBRATION_HIGH",
        alarm_name="Vibration High",
        severity="MEDIUM",
        operating_state="RUNNING",
    )

    assert first.event_id == second.event_id
    assert first.to_dict() == second.to_dict()
