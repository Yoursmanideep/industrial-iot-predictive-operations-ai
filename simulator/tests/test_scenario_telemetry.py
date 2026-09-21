from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from industrial_sim.domain.machine import Machine, MachineIdentity, MachineState
from industrial_sim.machines.base import MachineBehaviorContext
from industrial_sim.scenarios.catalog import load_scenario_catalog
from industrial_sim.scenarios.engine import ScenarioEngine
from industrial_sim.scenarios.telemetry import ScenarioAwareTelemetryEngine

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
RUN_ID = UUID("12345678-1234-5678-1234-567812345678")
START = datetime(2026, 9, 21, 6, 0, tzinfo=timezone.utc)


def machine() -> Machine:
    return Machine(
        identity=MachineIdentity(
            machine_id="CHN-L01-CNC01",
            plant_id="PLT-CHN-01",
            line_id="CHN-L01",
            machine_type="CNC",
        ),
        state=MachineState.RUNNING,
    )


def test_scenario_aware_telemetry_changes_affected_signals() -> None:
    catalog = load_scenario_catalog(CONFIG_DIR / "scenario_catalog.yaml")
    scenario_engine = ScenarioEngine(catalog)
    instance = scenario_engine.create_instance(
        RUN_ID, "CHN-L01-CNC01", "SCN-CNC-BRG", START, 1
    )
    progress, _ = scenario_engine.advance(
        instance,
        START + (instance.planned_end_at - START) * 0.50,
    )

    context = MachineBehaviorContext(
        simulation_seconds=0,
        workload_factor=0.80,
        ambient_temperature_c=28.0,
        health_factor=1.0,
        scenario_severity=0.0,
        event_time=START,
    )
    engine = ScenarioAwareTelemetryEngine.from_catalog(catalog)
    baseline = engine.generate(machine(), context)
    scenario_values = engine.generate(
        machine(),
        context,
        scenario_instance=instance,
        scenario_progress=progress,
    )

    assert scenario_values["vibration_mm_s"] > baseline["vibration_mm_s"]
    assert scenario_values["temperature_c"] > baseline["temperature_c"]
    assert scenario_values["power_kw"] > baseline["power_kw"]
    assert scenario_values["quality_score_pct"] < baseline["quality_score_pct"]
