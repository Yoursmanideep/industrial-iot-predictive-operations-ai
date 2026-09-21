from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from industrial_sim.domain.machine import Machine
from industrial_sim.domain.scenario import ScenarioInstance, ScenarioProgress
from industrial_sim.scenarios.catalog import ScenarioCatalog
from industrial_sim.scenarios.effects import ScenarioTelemetryEffectEngine
from industrial_sim.telemetry.base import TelemetryPhysicsContext
from industrial_sim.telemetry.physics import PHYSICS_BY_TYPE
from industrial_sim.machines.base import MachineBehaviorContext


@dataclass
class ScenarioAwareTelemetryEngine:
    catalog: ScenarioCatalog
    effects: ScenarioTelemetryEffectEngine

    def generate(
        self,
        machine: Machine,
        behavior_context: MachineBehaviorContext,
        scenario_instance: ScenarioInstance | None = None,
        scenario_progress: ScenarioProgress | None = None,
        event_time: datetime | None = None,
    ) -> dict[str, float]:
        event_time = event_time or behavior_context.event_time
        if event_time is None:
            raise ValueError("event_time is required for deterministic telemetry generation")
        provider = PHYSICS_BY_TYPE.get(machine.machine_type)
        if provider is None:
            raise KeyError(f"No telemetry physics registered for {machine.machine_type}")

        baseline = provider.generate(
            TelemetryPhysicsContext(
                machine=machine,
                behavior_context=behavior_context,
                event_time=event_time,
            )
        )
        if scenario_instance is None or scenario_progress is None:
            return baseline

        definition = self.catalog.get(scenario_instance.scenario_id)
        return self.effects.apply(
            baseline=baseline,
            definition=definition,
            instance_id=str(scenario_instance.scenario_instance_id),
            severity=scenario_progress.severity,
            event_time=event_time,
        )

    @classmethod
    def from_catalog(cls, catalog: ScenarioCatalog) -> "ScenarioAwareTelemetryEngine":
        return cls(catalog=catalog, effects=ScenarioTelemetryEffectEngine())
