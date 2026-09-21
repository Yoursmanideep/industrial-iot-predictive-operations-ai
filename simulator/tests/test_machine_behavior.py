from industrial_sim.domain.machine import Machine, MachineIdentity, MachineState
from industrial_sim.machines.base import MachineBehaviorContext
from industrial_sim.machines.profiles import load_machine_profiles
from industrial_sim.machines.registry import MachineBehaviorRegistry


def test_running_healthy_machine_is_production_eligible() -> None:
    catalog = load_machine_profiles("../../config/simulator_machine_profiles.yaml")
    registry = MachineBehaviorRegistry.with_generic_profiles(catalog)
    machine = Machine(
        identity=MachineIdentity(
            machine_id="CHN-L01-CNC01",
            plant_id="PLT-CHN-01",
            line_id="CHN-L01",
            machine_type="CNC",
        ),
        state=MachineState.RUNNING,
    )

    output = registry.get("CNC").evaluate(
        machine,
        MachineBehaviorContext(
            simulation_seconds=0,
            workload_factor=1.0,
            ambient_temperature_c=28.0,
            health_factor=1.0,
        ),
    )

    assert output.recommended_state is MachineState.RUNNING
    assert output.production_eligible is True
    assert output.telemetry_interval_seconds == 5


def test_idle_machine_is_not_production_eligible() -> None:
    catalog = load_machine_profiles("../../config/simulator_machine_profiles.yaml")
    registry = MachineBehaviorRegistry.with_generic_profiles(catalog)
    machine = Machine(
        identity=MachineIdentity(
            machine_id="CHN-L01-CNC01",
            plant_id="PLT-CHN-01",
            line_id="CHN-L01",
            machine_type="CNC",
        ),
        state=MachineState.IDLE,
    )

    output = registry.get("CNC").evaluate(
        machine,
        MachineBehaviorContext(
            simulation_seconds=0,
            workload_factor=1.0,
            ambient_temperature_c=28.0,
            health_factor=1.0,
        ),
    )

    assert output.production_eligible is False
