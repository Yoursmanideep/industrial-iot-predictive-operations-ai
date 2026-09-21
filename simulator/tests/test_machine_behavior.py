from datetime import datetime, timezone
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"

from industrial_sim.domain.machine import Machine, MachineIdentity, MachineState
from industrial_sim.machines.base import MachineBehaviorContext
from industrial_sim.machines.profiles import load_machine_profiles
from industrial_sim.machines.registry import MachineBehaviorRegistry


def cnc_machine(state: MachineState = MachineState.RUNNING) -> Machine:
    return Machine(
        identity=MachineIdentity(
            machine_id="CHN-L01-CNC01",
            plant_id="PLT-CHN-01",
            line_id="CHN-L01",
            machine_type="CNC",
        ),
        state=state,
    )


def test_running_healthy_machine_is_production_eligible() -> None:
    catalog = load_machine_profiles(CONFIG_DIR / "simulator_machine_profiles.yaml")
    registry = MachineBehaviorRegistry.with_generic_profiles(catalog)
    output = registry.get("CNC").evaluate(
        cnc_machine(),
        MachineBehaviorContext(
            simulation_seconds=0,
            workload_factor=1.0,
            ambient_temperature_c=28.0,
            health_factor=1.0,
            event_time=datetime(2026, 9, 21, 6, 0, tzinfo=timezone.utc),
        ),
    )

    assert output.recommended_state is MachineState.RUNNING
    assert output.production_eligible is True
    assert output.telemetry_interval_seconds == 5
    assert set(output.signal_inputs) == {
        "spindle_rpm",
        "vibration_mm_s",
        "temperature_c",
        "pressure_bar",
        "power_kw",
        "feed_rate_mm_min",
        "production_rate_unit_min",
        "quality_score_pct",
    }


def test_idle_machine_is_not_production_eligible() -> None:
    catalog = load_machine_profiles("../../config/simulator_machine_profiles.yaml")
    registry = MachineBehaviorRegistry.with_generic_profiles(catalog)
    output = registry.get("CNC").evaluate(
        cnc_machine(MachineState.IDLE),
        MachineBehaviorContext(
            simulation_seconds=0,
            workload_factor=1.0,
            ambient_temperature_c=28.0,
            health_factor=1.0,
            event_time=datetime(2026, 9, 21, 6, 0, tzinfo=timezone.utc),
        ),
    )

    assert output.production_eligible is False
    assert output.signal_inputs["spindle_rpm"] < 100


def test_machine_type_physics_is_deterministic() -> None:
    catalog = load_machine_profiles("../../config/simulator_machine_profiles.yaml")
    registry = MachineBehaviorRegistry.with_generic_profiles(catalog)
    context = MachineBehaviorContext(
        simulation_seconds=100,
        workload_factor=0.85,
        ambient_temperature_c=32.0,
        health_factor=0.95,
        scenario_severity=0.10,
        event_time=datetime(2026, 9, 21, 6, 1, 40, tzinfo=timezone.utc),
    )
    first = registry.get("CNC").evaluate(cnc_machine(), context).signal_inputs
    second = registry.get("CNC").evaluate(cnc_machine(), context).signal_inputs
    assert first == second
