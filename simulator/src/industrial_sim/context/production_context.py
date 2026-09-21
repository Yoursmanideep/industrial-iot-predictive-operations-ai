from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from industrial_sim.context.environment import EnvironmentReading
from industrial_sim.context.shift import ShiftContext
from industrial_sim.context.workload import WorkloadInputs, WorkloadModel, WorkloadResult


@dataclass(frozen=True)
class ProductionContext:
    event_time_utc: datetime
    plant_id: str
    line_id: str
    shift_id: str
    product_id: str | None
    product_cycle_time_seconds: float | None
    ambient_temperature_c: float
    utility_power_factor: float
    workload: WorkloadResult


class ProductionContextEngine:
    def __init__(self, environment_model, shift_resolver, workload_model: WorkloadModel) -> None:
        self.environment_model = environment_model
        self.shift_resolver = shift_resolver
        self.workload_model = workload_model

    def build(
        self,
        plant_id: str,
        line_id: str,
        event_time_utc: datetime,
        inputs: WorkloadInputs,
        product_id: str | None = None,
        product_cycle_time_seconds: float | None = None,
    ) -> ProductionContext:
        environment: EnvironmentReading = self.environment_model.reading(plant_id, event_time_utc)
        shift: ShiftContext = self.shift_resolver.resolve(event_time_utc)
        workload = self.workload_model.evaluate(inputs, shift, event_time_utc)
        return ProductionContext(
            event_time_utc=event_time_utc,
            plant_id=plant_id,
            line_id=line_id,
            shift_id=shift.shift_id,
            product_id=product_id,
            product_cycle_time_seconds=product_cycle_time_seconds,
            ambient_temperature_c=environment.ambient_temperature_c,
            utility_power_factor=environment.utility_power_factor,
            workload=workload,
        )
