from datetime import datetime, timezone

from industrial_sim.domain.machine import Machine, MachineIdentity, MachineState
from industrial_sim.machines.base import MachineBehaviorContext
from industrial_sim.machines.profiles import load_machine_profiles
from industrial_sim.telemetry.registry import TelemetryPhysicsRegistry


def build_machine(machine_type: str, machine_id: str) -> Machine:
    return Machine(
        identity=MachineIdentity(
            machine_id=machine_id,
            plant_id="PLT-CHN-01",
            line_id="CHN-L01",
            machine_type=machine_type,
        ),
        state=MachineState.RUNNING,
    )


def test_all_nine_types_emit_configured_signals() -> None:
    profiles = load_machine_profiles("../../config/simulator_machine_profiles.yaml")
    registry = TelemetryPhysicsRegistry.default()
    event_time = datetime(2026, 9, 21, 6, 0, tzinfo=timezone.utc)

    for index, machine_type in enumerate(profiles.profiles, start=1):
        profile = profiles.get(machine_type)
        machine = build_machine(
            machine_type,
            f"CHN-L01-{profile.code}{index:02d}",
        )
        context = MachineBehaviorContext(
            simulation_seconds=0,
            workload_factor=0.80,
            ambient_temperature_c=28.0,
            health_factor=1.0,
            event_time=event_time,
        )
        values = registry.generate(machine, context)
        assert set(values) == set(profile.telemetry_signals)
        assert all(value >= 0 for value in values.values())


def test_cnc_physics_is_deterministic() -> None:
    registry = TelemetryPhysicsRegistry.default()
    machine = build_machine("CNC", "CHN-L01-CNC01")
    context = MachineBehaviorContext(
        simulation_seconds=0,
        workload_factor=0.85,
        ambient_temperature_c=32.0,
        health_factor=0.95,
        scenario_severity=0.10,
        event_time=datetime(2026, 9, 21, 6, 1, 40, tzinfo=timezone.utc),
    )
    first = registry.generate(machine, context)
    second = registry.generate(machine, context)
    assert first == second


def test_cnc_degradation_increases_correlated_signals() -> None:
    registry = TelemetryPhysicsRegistry.default()
    machine = build_machine("CNC", "CHN-L01-CNC01")
    event_time = datetime(2026, 9, 21, 6, 0, tzinfo=timezone.utc)

    healthy = registry.generate(
        machine,
        MachineBehaviorContext(
            simulation_seconds=0,
            workload_factor=0.80,
            ambient_temperature_c=28.0,
            health_factor=1.0,
            scenario_severity=0.0,
            event_time=event_time,
        ),
    )
    degraded = registry.generate(
        machine,
        MachineBehaviorContext(
            simulation_seconds=0,
            workload_factor=0.80,
            ambient_temperature_c=28.0,
            health_factor=0.55,
            scenario_severity=0.45,
            event_time=event_time,
        ),
    )

    assert degraded["vibration_mm_s"] > healthy["vibration_mm_s"]
    assert degraded["temperature_c"] > healthy["temperature_c"]
    assert degraded["quality_score_pct"] < healthy["quality_score_pct"]
