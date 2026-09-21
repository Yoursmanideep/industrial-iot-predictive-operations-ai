from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from industrial_sim.domain.machine import Machine
from industrial_sim.lineage.identity import deterministic_event_id


@dataclass(frozen=True)
class OperationalEvent:
    event_id: str
    event_type: str
    schema_version: str
    event_time: datetime
    ingestion_time: datetime
    source_system: str
    plant_id: str
    line_id: str
    machine_id: str
    machine_type: str
    correlation_id: str | None = None
    causation_id: str | None = None
    operating_state: str | None = None
    previous_state: str | None = None
    new_state: str | None = None
    alarm_code: str | None = None
    alarm_name: str | None = None
    severity: str | None = None
    fault_code: str | None = None
    failure_mode_code: str | None = None
    message: str | None = None
    trigger_source: str | None = "SIMULATOR"
    estimated_duration_seconds: float | None = None
    is_planned: bool | None = None
    communication_gap_seconds: float | None = None
    simulator_run_id: str | None = None
    scenario_id: str | None = None
    scenario_instance_id: str | None = None
    generated_at_utc: datetime | None = None
    deterministic_seed: int | None = None
    generation_sequence: int | None = None
    generator_version: str | None = None
    configuration_version: str | None = None

    def to_dict(self) -> dict:
        result = {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "schema_version": self.schema_version,
            "event_time": self.event_time.isoformat(),
            "ingestion_time": self.ingestion_time.isoformat(),
            "source_system": self.source_system,
            "plant_id": self.plant_id,
            "line_id": self.line_id,
            "machine_id": self.machine_id,
            "machine_type": self.machine_type,
        }
        optional = {
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "operating_state": self.operating_state,
            "previous_state": self.previous_state,
            "new_state": self.new_state,
            "alarm_code": self.alarm_code,
            "alarm_name": self.alarm_name,
            "severity": self.severity,
            "fault_code": self.fault_code,
            "failure_mode_code": self.failure_mode_code,
            "message": self.message,
            "trigger_source": self.trigger_source,
            "estimated_duration_seconds": self.estimated_duration_seconds,
            "is_planned": self.is_planned,
            "communication_gap_seconds": self.communication_gap_seconds,
            "simulator_run_id": self.simulator_run_id,
            "scenario_id": self.scenario_id,
            "scenario_instance_id": self.scenario_instance_id,
            "generated_at_utc": self.generated_at_utc.isoformat() if self.generated_at_utc else None,
            "deterministic_seed": self.deterministic_seed,
            "generation_sequence": self.generation_sequence,
            "generator_version": self.generator_version,
            "configuration_version": self.configuration_version,
        }
        result.update({key: value for key, value in optional.items() if value is not None})
        return result


class OperationalEventFactory:
    def __init__(
        self,
        schema_version: str = "1.0.0",
        generator_version: str = "0.1.0",
        source_system: str = "simulator",
    ) -> None:
        self.schema_version = schema_version
        self.generator_version = generator_version
        self.source_system = source_system

    def build(
        self,
        run_id: UUID,
        machine: Machine,
        event_type: str,
        event_time: datetime,
        generation_sequence: int,
        seed: int,
        configuration_version: str,
        scenario_id: str | None = None,
        scenario_instance_id: str | None = None,
        correlation_id: str | None = None,
        causation_id: str | None = None,
        **kwargs,
    ) -> OperationalEvent:
        raw_id = deterministic_event_id(
            run_id,
            machine.machine_id,
            event_type,
            event_time.isoformat(),
            generation_sequence,
        )
        ingestion_time = event_time + timedelta(milliseconds=100 + (generation_sequence % 1401))
        return OperationalEvent(
            event_id=f"EVT-{raw_id}",
            event_type=event_type,
            schema_version=self.schema_version,
            event_time=event_time,
            ingestion_time=ingestion_time,
            source_system=self.source_system,
            plant_id=machine.plant_id,
            line_id=machine.line_id,
            machine_id=machine.machine_id,
            machine_type=machine.machine_type,
            correlation_id=correlation_id,
            causation_id=causation_id,
            simulator_run_id=f"RUN-{run_id}",
            scenario_id=scenario_id,
            scenario_instance_id=scenario_instance_id,
            generated_at_utc=event_time,
            deterministic_seed=seed,
            generation_sequence=generation_sequence,
            generator_version=self.generator_version,
            configuration_version=configuration_version,
            **kwargs,
        )
