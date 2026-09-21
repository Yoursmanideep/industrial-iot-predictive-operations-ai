from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from industrial_sim.domain.machine import Machine
from industrial_sim.machines.base import MachineBehaviorContext


@dataclass(frozen=True)
class TelemetryPhysicsContext:
    machine: Machine
    behavior_context: MachineBehaviorContext


class TelemetryPhysics(Protocol):
    machine_type: str

    def generate(self, context: TelemetryPhysicsContext) -> dict[str, float]:
        ...
