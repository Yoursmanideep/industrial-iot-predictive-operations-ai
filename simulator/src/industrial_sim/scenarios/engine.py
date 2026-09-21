from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID

from industrial_sim.domain.scenario import (
    ScenarioInstance,
    ScenarioProgress,
    ScenarioStage,
    ScenarioStatus,
    ScenarioTransition,
)
from industrial_sim.scenarios.catalog import ScenarioCatalog
from industrial_sim.scenarios.deterministic import (
    choose_duration_minutes,
    deterministic_scenario_instance_id,
)


@dataclass
class ScenarioEngine:
    catalog: ScenarioCatalog
    _active_by_machine: dict[str, UUID] = field(default_factory=dict, init=False, repr=False)

    def create_instance(
        self,
        simulator_run_id: UUID,
        machine_id: str,
        scenario_id: str,
        started_at: datetime,
        generation_sequence: int,
        correlation_id: str | None = None,
        scenario_instance_id: UUID | None = None,
    ) -> ScenarioInstance:
        definition = self.catalog.get(scenario_id)
        active_id = self._active_by_machine.get(machine_id)
        if active_id is not None and active_id != scenario_instance_id:
            raise ValueError(
                f"Machine {machine_id} already has an active scenario: {active_id}"
            )
        duration_minutes = choose_duration_minutes(
            simulator_run_id,
            machine_id,
            scenario_id,
            started_at,
            definition.progression_min_minutes,
            definition.progression_max_minutes,
        )
        deterministic_id = scenario_instance_id or deterministic_scenario_instance_id(
            simulator_run_id,
            machine_id,
            scenario_id,
            started_at,
            generation_sequence,
        )
        instance = ScenarioInstance(
            scenario_instance_id=deterministic_id,
            simulator_run_id=simulator_run_id,
            scenario_id=scenario_id,
            machine_id=machine_id,
            failure_mode_code=definition.failure_mode_code,
            started_at=started_at,
            planned_end_at=started_at + timedelta(minutes=duration_minutes),
            status=ScenarioStatus.ACTIVE,
            generation_sequence=generation_sequence,
            correlation_id=correlation_id,
        )
        self._active_by_machine[machine_id] = deterministic_id
        return instance

    def advance(
        self,
        instance: ScenarioInstance,
        at: datetime,
    ) -> tuple[ScenarioProgress, ScenarioTransition | None]:
        if instance.status not in {ScenarioStatus.ACTIVE, ScenarioStatus.INTERRUPTED}:
            return self._progress(instance, at, terminal=True), None

        previous = instance.stage
        progress = instance.normalized_progress(at)
        if progress < 0.25:
            stage = ScenarioStage.EARLY_DEGRADATION
        elif progress < 0.55:
            stage = ScenarioStage.ANOMALY
        elif progress < 0.80:
            stage = ScenarioStage.CRITICAL
        else:
            stage = ScenarioStage.FAILURE

        transition = None
        if stage is not previous:
            transition = ScenarioTransition(
                scenario_instance_id=instance.scenario_instance_id,
                from_stage=previous,
                to_stage=stage,
                event_time=at,
                reason_code="PROGRESSION_THRESHOLD",
            )
            instance.stage = stage

        if stage is ScenarioStage.FAILURE:
            instance.status = ScenarioStatus.FAILED
            instance.actual_end_at = at
            self._active_by_machine.pop(instance.machine_id, None)

        return self._progress(instance, at, terminal=stage is ScenarioStage.FAILURE), transition

    def intervene(
        self,
        instance: ScenarioInstance,
        at: datetime,
        intervention_event_id: str,
    ) -> ScenarioTransition | None:
        if instance.status is not ScenarioStatus.ACTIVE:
            return None
        if instance.stage not in {
            ScenarioStage.EARLY_DEGRADATION,
            ScenarioStage.ANOMALY,
            ScenarioStage.CRITICAL,
        }:
            return None

        previous = instance.stage
        instance.stage = ScenarioStage.MAINTENANCE
        instance.status = ScenarioStatus.AVOIDED
        instance.intervention_event_id = intervention_event_id
        instance.actual_end_at = at
        self._active_by_machine.pop(instance.machine_id, None)
        return ScenarioTransition(
            scenario_instance_id=instance.scenario_instance_id,
            from_stage=previous,
            to_stage=ScenarioStage.MAINTENANCE,
            event_time=at,
            reason_code="PREDICTIVE_INTERVENTION",
        )

    def complete_maintenance(
        self,
        instance: ScenarioInstance,
        at: datetime,
    ) -> ScenarioTransition:
        if instance.stage is not ScenarioStage.MAINTENANCE:
            raise ValueError("Scenario must be in MAINTENANCE before recovery")
        instance.stage = ScenarioStage.RECOVERY
        return ScenarioTransition(
            scenario_instance_id=instance.scenario_instance_id,
            from_stage=ScenarioStage.MAINTENANCE,
            to_stage=ScenarioStage.RECOVERY,
            event_time=at,
            reason_code="MAINTENANCE_COMPLETE",
        )

    def complete_recovery(
        self,
        instance: ScenarioInstance,
        at: datetime,
    ) -> ScenarioTransition:
        if instance.stage is not ScenarioStage.RECOVERY:
            raise ValueError("Scenario must be in RECOVERY before baseline")
        instance.stage = ScenarioStage.BASELINE
        instance.status = ScenarioStatus.RESOLVED
        instance.actual_end_at = at
        self._active_by_machine.pop(instance.machine_id, None)
        return ScenarioTransition(
            scenario_instance_id=instance.scenario_instance_id,
            from_stage=ScenarioStage.RECOVERY,
            to_stage=ScenarioStage.BASELINE,
            event_time=at,
            reason_code="RECOVERY_COMPLETE",
        )

    def _progress(
        self,
        instance: ScenarioInstance,
        at: datetime,
        terminal: bool,
    ) -> ScenarioProgress:
        progress = instance.normalized_progress(at)
        severity = min(1.0, progress)
        production_multiplier = max(0.0, 1.0 - 0.80 * severity)
        quality_multiplier = max(0.0, 1.0 - 0.60 * severity)
        if instance.stage in {ScenarioStage.FAILURE, ScenarioStage.MAINTENANCE, ScenarioStage.RECOVERY}:
            production_multiplier = 0.0 if instance.stage is not ScenarioStage.RECOVERY else 0.25
        return ScenarioProgress(
            scenario_instance_id=instance.scenario_instance_id,
            stage=instance.stage,
            status=instance.status,
            severity=severity,
            normalized_progress=progress,
            production_multiplier=production_multiplier,
            quality_multiplier=quality_multiplier,
            terminal=terminal,
        )
