from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from industrial_sim.domain.machine import Machine, MachineState, MachineStateTransition


DEFAULT_ALLOWED_TRANSITIONS: dict[MachineState, frozenset[MachineState]] = {
    MachineState.OFFLINE: frozenset(
        {MachineState.SETUP, MachineState.MAINTENANCE, MachineState.RUNNING, MachineState.IDLE}
    ),
    MachineState.SETUP: frozenset(
        {MachineState.RUNNING, MachineState.IDLE, MachineState.STARVED, MachineState.FAULT, MachineState.OFFLINE}
    ),
    MachineState.RUNNING: frozenset(
        {
            MachineState.IDLE,
            MachineState.SETUP,
            MachineState.STARVED,
            MachineState.BLOCKED,
            MachineState.FAULT,
            MachineState.MAINTENANCE,
            MachineState.OFFLINE,
        }
    ),
    MachineState.IDLE: frozenset(
        {
            MachineState.RUNNING,
            MachineState.SETUP,
            MachineState.STARVED,
            MachineState.MAINTENANCE,
            MachineState.OFFLINE,
        }
    ),
    MachineState.STARVED: frozenset(
        {
            MachineState.RUNNING,
            MachineState.IDLE,
            MachineState.SETUP,
            MachineState.BLOCKED,
            MachineState.FAULT,
            MachineState.OFFLINE,
        }
    ),
    MachineState.BLOCKED: frozenset(
        {
            MachineState.RUNNING,
            MachineState.IDLE,
            MachineState.STARVED,
            MachineState.FAULT,
            MachineState.MAINTENANCE,
            MachineState.OFFLINE,
        }
    ),
    MachineState.FAULT: frozenset(
        {MachineState.MAINTENANCE, MachineState.RECOVERY, MachineState.OFFLINE}
    ),
    MachineState.MAINTENANCE: frozenset(
        {MachineState.RECOVERY, MachineState.OFFLINE}
    ),
    MachineState.RECOVERY: frozenset(
        {MachineState.RUNNING, MachineState.IDLE, MachineState.SETUP, MachineState.FAULT}
    ),
}


@dataclass
class MachineStateMachine:
    allowed_transitions: dict[MachineState, frozenset[MachineState]] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.allowed_transitions is None:
            self.allowed_transitions = DEFAULT_ALLOWED_TRANSITIONS

    def can_transition(
        self,
        from_state: MachineState,
        to_state: MachineState,
    ) -> bool:
        return to_state in self.allowed_transitions.get(from_state, frozenset())

    def transition(
        self,
        machine: Machine,
        to_state: MachineState,
        event_time: datetime,
        reason_code: str,
    ) -> MachineStateTransition:
        if not self.can_transition(machine.state, to_state):
            raise ValueError(
                f"Invalid machine state transition: {machine.state} -> {to_state}"
            )

        transition = MachineStateTransition(
            machine_id=machine.machine_id,
            from_state=machine.state,
            to_state=to_state,
            event_time=event_time,
            reason_code=reason_code,
        )
        machine.state = to_state
        machine.state_since = event_time
        return transition
