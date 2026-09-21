from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from industrial_sim.domain.machine import Machine
from industrial_sim.machines.base import MachineBehaviorContext
from industrial_sim.telemetry.base import TelemetryPhysicsContext
from industrial_sim.telemetry.physics import PHYSICS_BY_TYPE


@dataclass(frozen=True)
class TelemetryPhysicsRegistry:
    providers: dict[str, object]

    @classmethod
    def default(cls) -> "TelemetryPhysicsRegistry":
        return cls(dict(PHYSICS_BY_TYPE))

    def get(self, machine_type: str):
        try:
            return self.providers[machine_type]
        except KeyError as exc:
            raise KeyError(f"No telemetry physics registered for {machine_type}") from exc

    def generate(self, machine: Machine, context: MachineBehaviorContext) -> dict[str, float]:
        event_time = context.event_time
        if event_time is None:
            event_time = datetime.fromtimestamp(context.simulation_seconds, tz=timezone.utc)
        return self.get(machine.machine_type).generate(
            TelemetryPhysicsContext(
                machine=machine,
                behavior_context=context,
                event_time=event_time,
            )
        )
