from datetime import datetime, timezone

import pytest

from industrial_sim.domain.machine import Machine, MachineIdentity, MachineState
from industrial_sim.machines.state_machine import MachineStateMachine


def build_machine() -> Machine:
    return Machine(identity=MachineIdentity(
        machine_id="CHN-L01-CNC01",
        plant_id="PLT-CHN-01",
        line_id="CHN-L01",
        machine_type="CNC",
    ))


def test_all_factory_states_are_present() -> None:
    assert {state.value for state in MachineState} == {
        "RUNNING", "IDLE", "SETUP", "STARVED", "BLOCKED",
        "FAULT", "MAINTENANCE", "OFFLINE", "RECOVERY",
    }


def test_valid_transition_updates_machine() -> None:
    machine = build_machine()
    engine = MachineStateMachine()
    event_time = datetime(2026, 9, 21, 6, 0, tzinfo=timezone.utc)
    transition = engine.transition(machine, MachineState.RUNNING, event_time, "STARTUP_COMPLETE")
    assert transition.from_state is MachineState.OFFLINE
    assert transition.to_state is MachineState.RUNNING
    assert machine.state is MachineState.RUNNING
    assert machine.state_since == event_time


def test_invalid_transition_is_rejected() -> None:
    machine = build_machine()
    engine = MachineStateMachine()
    event_time = datetime(2026, 9, 21, 6, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        engine.transition(machine, MachineState.RECOVERY, event_time, "INVALID_DIRECT_RECOVERY")


def test_same_state_transition_is_rejected() -> None:
    machine = build_machine()
    engine = MachineStateMachine()
    with pytest.raises(ValueError):
        engine.transition(
            machine,
            MachineState.OFFLINE,
            datetime(2026, 9, 21, 6, 0, tzinfo=timezone.utc),
            "NO_OP",
        )
