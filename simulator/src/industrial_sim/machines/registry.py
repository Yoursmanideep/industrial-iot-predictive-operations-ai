from __future__ import annotations

from datetime import datetime, timezone

from industrial_sim.domain.machine import Machine
from industrial_sim.machines.base import (
    MachineBehavior,
    MachineBehaviorContext,
    MachineBehaviorOutput,
)
from industrial_sim.machines.profiles import MachineProfileCatalog
from industrial_sim.telemetry.physics import PHYSICS_BY_TYPE
from industrial_sim.telemetry.base import TelemetryPhysicsContext


class TypeSpecificMachineBehavior:
    """Machine behavior that combines eligibility rules with physical telemetry."""

    def __init__(self, machine_type: str, profiles: MachineProfileCatalog) -> None:
        self.machine_type = machine_type
        self._profiles = profiles
        if machine_type not in PHYSICS_BY_TYPE:
            raise KeyError(f"No telemetry physics registered for {machine_type}")

    def evaluate(
        self,
        machine: Machine,
        context: MachineBehaviorContext,
    ) -> MachineBehaviorOutput:
        profile = self._profiles.get(machine.machine_type)
        production_eligible = (
            machine.state.value in profile.productive_states
            and context.health_factor >= profile.minimum_health_factor
            and context.workload_factor <= profile.max_workload_factor
        )
        event_time = context.event_time
        if event_time is None:
            event_time = datetime.fromtimestamp(
                context.simulation_seconds,
                tz=timezone.utc,
            )
        signals = PHYSICS_BY_TYPE[machine.machine_type].generate(
            TelemetryPhysicsContext(
                machine=machine,
                behavior_context=context,
                event_time=event_time,
            )
        )
        return MachineBehaviorOutput(
            recommended_state=machine.state,
            production_eligible=production_eligible,
            telemetry_interval_seconds=profile.default_telemetry_interval_seconds,
            signal_inputs=signals,
        )


class MachineBehaviorRegistry:
    def __init__(self, profiles: MachineProfileCatalog) -> None:
        self._profiles = profiles
        self._behaviors: dict[str, MachineBehavior] = {}

    def register(self, behavior: MachineBehavior) -> None:
        if behavior.machine_type in self._behaviors:
            raise ValueError(
                f"Machine behavior already registered: {behavior.machine_type}"
            )
        self._behaviors[behavior.machine_type] = behavior

    def get(self, machine_type: str) -> MachineBehavior:
        if machine_type not in self._behaviors:
            raise KeyError(f"No behavior registered for {machine_type}")
        return self._behaviors[machine_type]

    @classmethod
    def with_generic_profiles(
        cls,
        profiles: MachineProfileCatalog,
    ) -> "MachineBehaviorRegistry":
        registry = cls(profiles)
        for machine_type in profiles.profiles:
            registry.register(TypeSpecificMachineBehavior(machine_type, profiles))
        return registry
