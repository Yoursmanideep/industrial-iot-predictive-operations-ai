from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from industrial_sim.domain.machine import Machine, MachineState


@dataclass(frozen=True)
class MachineBehaviorContext:
    simulation_seconds: float
    workload_factor: float
    ambient_temperature_c: float
    health_factor: float
    scenario_stage: str | None = None


@dataclass(frozen=True)
class MachineBehaviorOutput:
    recommended_state: MachineState
    production_eligible: bool
    telemetry_interval_seconds: int
    signal_inputs: dict[str, float]


class MachineBehavior(Protocol):
    machine_type: str

    def evaluate(
        self,
        machine: Machine,
        context: MachineBehaviorContext,
    ) -> MachineBehaviorOutput:
        ...
