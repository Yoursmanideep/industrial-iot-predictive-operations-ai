from __future__ import annotations

from dataclasses import dataclass

from industrial_sim.domain.machine import Machine
from industrial_sim.machines.base import (
    MachineBehavior,
    MachineBehaviorContext,
    MachineBehaviorOutput,
)
from industrial_sim.machines.profiles import MachineProfileCatalog


@dataclass(frozen=True)
class GenericMachineBehavior:
    machine_type: str
    profiles: MachineProfileCatalog

    def evaluate(
        self,
        machine: Machine,
        context: MachineBehaviorContext,
    ) -> MachineBehaviorOutput:
        profile = self.profiles.get(machine.machine_type)
        production_eligible = (
            machine.state.value in profile.productive_states
            and context.health_factor >= profile.minimum_health_factor
            and context.workload_factor <= profile.max_workload_factor
        )
        return MachineBehaviorOutput(
            recommended_state=machine.state,
            production_eligible=production_eligible,
            telemetry_interval_seconds=profile.default_telemetry_interval_seconds,
            signal_inputs={},
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
    def with_generic_profiles(cls, profiles: MachineProfileCatalog) -> "MachineBehaviorRegistry":
        registry = cls(profiles)
        for machine_type in profiles.profiles:
            registry.register(GenericMachineBehavior(machine_type, profiles))
        return registry
