from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class MachineState(StrEnum):
    RUNNING = "RUNNING"
    IDLE = "IDLE"
    SETUP = "SETUP"
    STARVED = "STARVED"
    BLOCKED = "BLOCKED"
    FAULT = "FAULT"
    MAINTENANCE = "MAINTENANCE"
    OFFLINE = "OFFLINE"
    RECOVERY = "RECOVERY"


@dataclass(frozen=True)
class MachineIdentity:
    machine_id: str
    plant_id: str
    line_id: str
    machine_type: str
    machine_model: str | None = None


@dataclass(frozen=True)
class MachineStateTransition:
    machine_id: str
    from_state: MachineState
    to_state: MachineState
    event_time: datetime
    reason_code: str
    correlation_id: str | None = None
    causation_id: UUID | None = None

    def __post_init__(self) -> None:
        if self.event_time.tzinfo is None:
            raise ValueError("event_time must be timezone-aware.")
        if self.from_state is self.to_state:
            raise ValueError("A state transition must change machine state.")


@dataclass
class Machine:
    identity: MachineIdentity
    state: MachineState = MachineState.OFFLINE
    state_since: datetime | None = None
    active_scenario_instance_id: str | None = None
    active_work_order_id: str | None = None

    @property
    def machine_id(self) -> str:
        return self.identity.machine_id

    @property
    def plant_id(self) -> str:
        return self.identity.plant_id

    @property
    def line_id(self) -> str:
        return self.identity.line_id

    @property
    def machine_type(self) -> str:
        return self.identity.machine_type
