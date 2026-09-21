from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from industrial_sim.domain.machine import Machine
from industrial_sim.lineage.identity import deterministic_event_id


@dataclass(frozen=True)
class MachineTelemetryEvent:
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
    operating_state: str
    signals: dict[str, float]
    correlation_id: str | None = None
    causation_id: str | None = None
    simulator_run_id: str | None = None
    scenario_id: str | None = None
    scenario_instance_id: str | None = None
    generated_at_utc: datetime | None = None
    deterministic_seed: int | None = None
    generation_sequence: int | None = None
    generator_version: str | None = None
    configuration_version: str | None = None

    def to_dict(self) -> dict:
        payload = {
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
            "operating_state": self.operating_state,
            **self.signals,
        }
        optional = {
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "simulator_run_id": self.simulator_run_id,
            "scenario_id": self.scenario_id,
            "scenario_instance_id": self.scenario_instance_id,
            "generated_at_utc": self.generated_at_utc.isoformat() if self.generated_at_utc else None,
            "deterministic_seed": self.deterministic_seed,
            "generation_sequence": self.generation_sequence,
            "generator_version": self.generator_version,
            "configuration_version": self.configuration_version,
        }
        payload.update({key: value for key, value in optional.items() if value is not None})
        return payload


class TelemetryEventFactory:
    def __init__(self, schema_version: str = "1.0.0", generator_version: str = "0.1.0") -> None:
        self.schema_version = schema_version
        self.generator_version = generator_version

    def build(
        self,
        run_id: UUID,
        machine: Machine,
        event_time: datetime,
        generation_sequence: int,
        seed: int,
        configuration_version: str,
        signals: dict[str, float],
        scenario_id: str | None = None,
        scenario_instance_id: str | None = None,
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> MachineTelemetryEvent:
        raw_id = deterministic_event_id(
            run_id,
            machine.machine_id,
            "MachineTelemetry",
            event_time.isoformat(),
            generation_sequence,
        )
        return MachineTelemetryEvent(
            event_id=f"EVT-{raw_id}",
            event_type="MachineTelemetry",
            schema_version=self.schema_version,
            event_time=event_time,
            ingestion_time=event_time + timedelta(milliseconds=100 + generation_sequence % 1401),
            source_system="simulator",
            plant_id=machine.plant_id,
            line_id=machine.line_id,
            machine_id=machine.machine_id,
            machine_type=machine.machine_type,
            operating_state=machine.state.value,
            signals=dict(signals),
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
        )
