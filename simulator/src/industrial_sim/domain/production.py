from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class ProductionOrderStatus(StrEnum):
    CREATED = "CREATED"
    RELEASED = "RELEASED"
    STARTED = "STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class BatchStatus(StrEnum):
    CREATED = "CREATED"
    STARTED = "STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class ProductDefinition:
    product_id: str
    product_family: str
    unit_of_measure: str
    standard_cycle_time_seconds: float
    standard_unit_cost_inr: float
    route: tuple[str, ...]
    quality_baseline_pct: float
    workload_factor: float


@dataclass(frozen=True)
class LineCapacitySnapshot:
    line_id: str
    event_time: datetime
    bottleneck_rate_units_min: float
    available: bool
    active_machine_ids: tuple[str, ...]
    blocked_machine_ids: tuple[str, ...]
    scenario_multiplier: float = 1.0


@dataclass
class ProductionOrder:
    production_order_id: UUID
    plant_id: str
    line_id: str
    product_id: str
    planned_quantity: int
    quantity_uom: str
    planned_start_time: datetime
    planned_end_time: datetime
    status: ProductionOrderStatus = ProductionOrderStatus.CREATED
    actual_quantity: float = 0.0
    good_quantity: float = 0.0
    rejected_quantity: float = 0.0
    actual_start_time: datetime | None = None
    actual_end_time: datetime | None = None

    def __post_init__(self) -> None:
        if self.planned_quantity <= 0:
            raise ValueError("planned_quantity must be greater than zero")
        if self.planned_end_time <= self.planned_start_time:
            raise ValueError("planned_end_time must be after planned_start_time")

    @property
    def remaining_quantity(self) -> float:
        return max(0.0, self.planned_quantity - self.actual_quantity)

    def record_output(self, actual: float, good: float, rejected: float) -> None:
        if min(actual, good, rejected) < 0:
            raise ValueError("Production quantities cannot be negative")
        if good + rejected > actual + 1e-9:
            raise ValueError("good + rejected cannot exceed actual")
        self.actual_quantity += actual
        self.good_quantity += good
        self.rejected_quantity += rejected
        if self.good_quantity + self.rejected_quantity > self.actual_quantity + 1e-9:
            raise ValueError("Cumulative production quantity invariant violated")


@dataclass
class ProductionBatch:
    batch_id: UUID
    production_order_id: UUID
    plant_id: str
    line_id: str
    product_id: str
    planned_quantity: int
    batch_sequence: int
    status: BatchStatus = BatchStatus.CREATED
    actual_quantity: float = 0.0
    good_quantity: float = 0.0
    rejected_quantity: float = 0.0
    actual_start_time: datetime | None = None
    actual_end_time: datetime | None = None

    @property
    remaining_quantity(self) -> float:
        return max(0.0, self.planned_quantity - self.actual_quantity)