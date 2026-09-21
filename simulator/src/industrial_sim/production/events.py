from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from industrial_sim.domain.production import ProductionBatch, ProductionOrder
from industrial_sim.lineage.identity import deterministic_event_id


@dataclass(frozen=True)
class ProductionEvent:
    event_id: str
    event_type: str
    schema_version: str
    event_time: datetime
    ingestion_time: datetime
    source_system: str
    plant_id: str
    production_order_id: str
    line_id: str | None = None
    machine_id: str | None = None
    batch_id: str | None = None
    product_id: str | None = None
    operation_id: str | None = None
    production_sequence: int | None = None
    planned_quantity: float | None = None
    actual_quantity: float | None = None
    good_quantity: float | None = None
    rejected_quantity: float | None = None
    quantity_uom: str | None = None
    planned_start_time: datetime | None = None
    planned_end_time: datetime | None = None
    actual_start_time: datetime | None = None
    actual_end_time: datetime | None = None
    pause_reason_code: str | None = None
    loss_reason_code: str | None = None
    loss_category: str | None = None
    loss_quantity: float | None = None
    loss_duration_seconds: float | None = None
    downtime_event_id: str | None = None
    machine_fault_event_id: str | None = None
    notes: str | None = None
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
        result = {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "schema_version": self.schema_version,
            "event_time": self.event_time.isoformat(),
            "ingestion_time": self.ingestion_time.isoformat(),
            "source_system": self.source_system,
            "plant_id": self.plant_id,
            "production_order_id": self.production_order_id,
        }
        values = self.__dict__.copy()
        for key in ("event_time", "ingestion_time", "planned_start_time", "planned_end_time", "actual_start_time", "actual_end_time", "generated_at_utc"):
            if values.get(key) is not None and hasattr(values[key], "isoformat"):
                values[key] = values[key].isoformat()
        values = {k: v for k, v in values.items() if k not in result and v is not None}
        result.update(values)
        return result


class ProductionEventFactory:
    def __init__(self, schema_version: str = "1.0.0", generator_version: str = "0.1.0", source_system: str = "simulator") -> None:
        self.schema_version = schema_version
        self.generator_version = generator_version
        self.source_system = source_system

    def build(
        self,
        run_id: UUID,
        production_order: ProductionOrder,
        event_type: str,
        event_time: datetime,
        generation_sequence: int,
        deterministic_seed: int,
        configuration_version: str,
        batch: ProductionBatch | None = None,
        causation_id: str | None = None,
        **kwargs,
    ) -> ProductionEvent:
        entity_key = str(batch.batch_id) if batch else str(production_order.production_order_id)
        event_uuid = deterministic_event_id(
            run_id, entity_key, event_type, event_time.isoformat(), generation_sequence
        )
        line_id = kwargs.pop("line_id", production_order.line_id)
        product_id = kwargs.pop("product_id", production_order.product_id)
        machine_id = kwargs.pop("machine_id", None)
        operation_id = kwargs.pop("operation_id", None)
        batch_id = kwargs.pop("batch_id", f"BAT-{batch.batch_id}" if batch else None)
        correlation_id = kwargs.pop("correlation_id", f"PO-{production_order.production_order_id}")
        return ProductionEvent(
            event_id=f"EVT-{event_uuid}",
            event_type=event_type,
            schema_version=self.schema_version,
            event_time=event_time,
            ingestion_time=event_time + timedelta(milliseconds=100 + generation_sequence % 1401),
            source_system=self.source_system,
            plant_id=production_order.plant_id,
            production_order_id=f"PO-{production_order.production_order_id}",
            line_id=line_id,
            machine_id=machine_id,
            batch_id=batch_id,
            product_id=product_id,
            operation_id=operation_id,
            correlation_id=correlation_id,
            causation_id=causation_id,
            simulator_run_id=f"RUN-{run_id}",
            deterministic_seed=deterministic_seed,
            generation_sequence=generation_sequence,
            generated_at_utc=event_time,
            generator_version=self.generator_version,
            configuration_version=configuration_version,
            **kwargs,
        )