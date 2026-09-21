from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID


class ScenarioStage(StrEnum):
    BASELINE = "BASELINE"
    EARLY_DEGRADATION = "EARLY_DEGRADATION"
    ANOMALY = "ANOMALY"
    CRITICAL = "CRITICAL"
    FAILURE = "FAILURE"
    MAINTENANCE = "MAINTENANCE"
    RECOVERY = "RECOVERY"


class ScenarioStatus(StrEnum):
    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    INTERRUPTED = "INTERRUPTED"
    FAILED = "FAILED"
    RESOLVED = "RESOLVED"
    AVOIDED = "AVOIDED"


@dataclass(frozen=True)
class ScenarioDefinition:
    scenario_id: str
    failure_mode_code: str
    machine_type_code: str
    description: str
    trigger: str
    progression_min_minutes: int
    progression_max_minutes: int
    affected_signals: tuple[str, ...]
    behavior: dict[str, str]
    production_effect: str | None = None
    maintenance_type: str | None = None

    def __post_init__(self) -> None:
        if self.progression_min_minutes <= 0:
            raise ValueError("progression_min_minutes must be positive")
        if self.progression_max_minutes < self.progression_min_minutes:
            raise ValueError("progression_max_minutes cannot be below minimum")


@dataclass
class ScenarioInstance:
    scenario_instance_id: UUID
    simulator_run_id: UUID
    scenario_id: str
    machine_id: str
    failure_mode_code: str
    started_at: datetime
    planned_end_at: datetime
    stage: ScenarioStage = ScenarioStage.EARLY_DEGRADATION
    status: ScenarioStatus = ScenarioStatus.PLANNED
    actual_end_at: datetime | None = None
    intervention_event_id: str | None = None
    failure_event_id: str | None = None
    correlation_id: str | None = None
    generation_sequence: int = 0

    def elapsed_seconds(self, at: datetime) -> float:
        return max(0.0, (at - self.started_at).total_seconds())

    def duration_seconds(self) -> float:
        return max(1.0, (self.planned_end_at - self.started_at).total_seconds())

    def normalized_progress(self, at: datetime) -> float:
        return min(1.0, self.elapsed_seconds(at) / self.duration_seconds())


@dataclass(frozen=True)
class ScenarioProgress:
    scenario_instance_id: UUID
    stage: ScenarioStage
    status: ScenarioStatus
    severity: float
    normalized_progress: float
    production_multiplier: float
    quality_multiplier: float
    terminal: bool


@dataclass(frozen=True)
class ScenarioTransition:
    scenario_instance_id: UUID
    from_stage: ScenarioStage
    to_stage: ScenarioStage
    event_time: datetime
    reason_code: str

    def __post_init__(self) -> None:
        if self.event_time.tzinfo is None:
            raise ValueError("event_time must be timezone-aware")
        if self.from_stage is self.to_stage:
            raise ValueError("Scenario transition must change stage")
