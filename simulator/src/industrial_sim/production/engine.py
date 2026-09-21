from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID

import yaml

from industrial_sim.context.production_context import ProductionContext
from industrial_sim.domain.production import (
    ProductionBatch,
    ProductionOrder,
    ProductionOrderStatus,
    BatchStatus,
)
from industrial_sim.engine.context import SimulationContext
from industrial_sim.production.catalog import ProductionCatalog
from industrial_sim.production.events import ProductionEvent, ProductionEventFactory
from industrial_sim.production.identity import (
    deterministic_batch_id,
    deterministic_operation_id,
    deterministic_production_order_id,
)
from industrial_sim.production.line_engine import (
    LineExecutionEngine,
    MachineExecutionInput,
)


@dataclass
class ProductionExecutionEngine:
    catalog: ProductionCatalog
    line_engine: LineExecutionEngine
    event_factory: ProductionEventFactory
    deterministic_seed: int
    configuration_version: str
    generator_version: str = "0.1.0"

    @classmethod
    def from_config(
        cls,
        catalog: ProductionCatalog,
        config_path: str | Path,
        deterministic_seed: int,
        configuration_version: str,
    ) -> "ProductionExecutionEngine":
        document = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise ValueError("Production configuration must be a mapping")
        return cls(
            catalog=catalog,
            line_engine=LineExecutionEngine(document),
            event_factory=ProductionEventFactory(
                generator_version="0.1.0",
                source_system="simulator",
            ),
            deterministic_seed=deterministic_seed,
            configuration_version=configuration_version,
        )

    def create_order(
        self,
        context: SimulationContext,
        plant_id: str,
        line_id: str,
        product_id: str,
        planned_quantity: int,
        planned_start_time: datetime | None = None,
        production_sequence: int = 1,
    ) -> tuple[ProductionOrder, list[ProductionEvent]]:
        if product_id not in self.catalog.products:
            raise ValueError(f"Unknown product_id: {product_id}")
        if line_id not in self.catalog.lines:
            raise ValueError(f"Unknown line_id: {line_id}")
        product = self.catalog.product(product_id)
        if any(machine_type not in self.catalog.machines_by_line_type[line_id] for machine_type in product.route):
            raise ValueError(
                f"Product {product_id} route is not executable on {line_id}"
            )

        start = planned_start_time or context.current_time
        duration_seconds = max(
            900.0,
            planned_quantity * product.standard_cycle_time_seconds / 0.82,
        )
        order_id = deterministic_production_order_id(
            context.simulator_run_id,
            plant_id,
            line_id,
            start,
            production_sequence,
        )
        order = ProductionOrder(
            production_order_id=order_id,
            plant_id=plant_id,
            line_id=line_id,
            product_id=product_id,
            planned_quantity=planned_quantity,
            quantity_uom=product.unit_of_measure,
            planned_start_time=start,
            planned_end_time=start + timedelta(seconds=duration_seconds),
        )
        event = self.event_factory.build(
            context.simulator_run_id,
            order,
            "ProductionOrderCreated",
            start,
            context.next_sequence(),
            context.deterministic_seed,
            context.configuration_version,
            product_id=product_id,
            planned_quantity=planned_quantity,
            quantity_uom=product.unit_of_measure,
            planned_start_time=start,
            planned_end_time=order.planned_end_time,
        )
        return order, [event]

    def create_batches(
        self,
        context: SimulationContext,
        order: ProductionOrder,
        batch_count: int,
    ) -> list[ProductionBatch]:
        if not 1 <= batch_count <= 8:
            raise ValueError("batch_count must be between 1 and 8")
        batch_count = min(batch_count, order.planned_quantity)
        base = order.planned_quantity // batch_count
        remainder = order.planned_quantity % batch_count
        batches: list[ProductionBatch] = []
        for index in range(1, batch_count + 1):
            quantity = base + (1 if index <= remainder else 0)
            batch_id = deterministic_batch_id(
                context.simulator_run_id,
                order.production_order_id,
                index,
            )
            batches.append(
                ProductionBatch(
                    batch_id=batch_id,
                    production_order_id=order.production_order_id,
                    plant_id=order.plant_id,
                    line_id=order.line_id,
                    product_id=order.product_id,
                    planned_quantity=quantity,
                    batch_sequence=index,
                )
            )
        if sum(batch.planned_quantity for batch in batches) != order.planned_quantity:
            raise ValueError("Batch quantities must exactly equal order quantity")
        return batches

    def release_order(
        self,
        context: SimulationContext,
        order: ProductionOrder,
    ) -> ProductionEvent:
        self._require_order_status(order, {ProductionOrderStatus.CREATED})
        order.status = ProductionOrderStatus.RELEASED
        return self.event_factory.build(
            context.simulator_run_id,
            order,
            "ProductionOrderReleased",
            context.current_time,
            context.next_sequence(),
            context.deterministic_seed,
            context.configuration_version,
            product_id=order.product_id,
            planned_quantity=order.planned_quantity,
            quantity_uom=order.quantity_uom,
        )

    def start_order(
        self,
        context: SimulationContext,
        order: ProductionOrder,
    ) -> ProductionEvent:
        self._require_order_status(
            order,
            {ProductionOrderStatus.RELEASED, ProductionOrderStatus.STARTED},
        )
        if order.status is ProductionOrderStatus.RELEASED:
            order.status = ProductionOrderStatus.STARTED
        if order.actual_start_time is None:
            order.actual_start_time = context.current_time
        return self.event_factory.build(
            context.simulator_run_id,
            order,
            "ProductionStarted",
            context.current_time,
            context.next_sequence(),
            context.deterministic_seed,
            context.configuration_version,
            line_id=order.line_id,
            actual_start_time=order.actual_start_time,
        )

    def start_batch(
        self,
        context: SimulationContext,
        order: ProductionOrder,
        batch: ProductionBatch,
        operation_sequence: int = 1,
    ) -> list[ProductionEvent]:
        self._require_order_status(
            order,
            {
                ProductionOrderStatus.STARTED,
                ProductionOrderStatus.IN_PROGRESS,
            },
        )
        if batch.status is not BatchStatus.CREATED:
            raise ValueError("Only CREATED batches can be started")

        order.status = ProductionOrderStatus.IN_PROGRESS
        batch.status = BatchStatus.STARTED
        batch.actual_start_time = context.current_time
        operation_id = deterministic_operation_id(
            context.simulator_run_id,
            order.production_order_id,
            batch.batch_sequence,
            operation_sequence,
        )

        event = self.event_factory.build(
            context.simulator_run_id,
            order,
            "BatchStarted",
            context.current_time,
            context.next_sequence(),
            context.deterministic_seed,
            context.configuration_version,
            batch=batch,
            line_id=order.line_id,
            operation_id=f"OP-{operation_id}",
            actual_start_time=batch.actual_start_time,
        )
        return [event]

    def advance_batch(
        self,
        context: SimulationContext,
        order: ProductionOrder,
        batch: ProductionBatch,
        line_snapshot,
        production_context: ProductionContext,
        elapsed_seconds: float,
        scenario_quality_multiplier: float = 1.0,
        machine_fault_event_id: str | None = None,
        scenario_id: str | None = None,
        scenario_instance_id: str | None = None,
    ) -> list[ProductionEvent]:
        if batch.status not in {BatchStatus.STARTED, BatchStatus.IN_PROGRESS}:
            raise ValueError("Batch must be STARTED or IN_PROGRESS")
        if elapsed_seconds <= 0:
            raise ValueError("elapsed_seconds must be positive")
        if batch.remaining_quantity <= 0:
            return []

        result = self.line_engine.advance_batch(
            batch=batch,
            snapshot=line_snapshot,
            context=production_context,
            elapsed_seconds=elapsed_seconds,
            quality_multiplier=(
                self.catalog.product(batch.product_id).quality_baseline_pct / 100.0
            ) * max(0.0, min(1.0, scenario_quality_multiplier)),
        )
        batch.status = BatchStatus.IN_PROGRESS
        events: list[ProductionEvent] = []

        if result.produced_quantity > 0:
            batch.actual_quantity += result.produced_quantity
            batch.good_quantity += result.good_quantity
            batch.rejected_quantity += result.rejected_quantity
            order.record_output(
                result.produced_quantity,
                result.good_quantity,
                result.rejected_quantity,
            )
            operation_id = deterministic_operation_id(
                context.simulator_run_id,
                order.production_order_id,
                batch.batch_sequence,
                1,
            )
            unit_event = self.event_factory.build(
                context.simulator_run_id,
                order,
                "UnitProduced",
                context.current_time,
                context.next_sequence(),
                context.deterministic_seed,
                context.configuration_version,
                batch=batch,
                line_id=order.line_id,
                operation_id=f"OP-{operation_id}",
                actual_quantity=result.produced_quantity,
                good_quantity=result.good_quantity,
                rejected_quantity=result.rejected_quantity,
                quantity_uom=order.quantity_uom,
                machine_id=(
                    result.active_machine_ids[0] if result.active_machine_ids else None
                ),
                scenario_id=scenario_id,
                scenario_instance_id=scenario_instance_id,
            )
            events.append(unit_event)

        if not result.available:
            loss = self.event_factory.build(
                context.simulator_run_id,
                order,
                "ProductionLossRecorded",
                context.current_time,
                context.next_sequence(),
                context.deterministic_seed,
                context.configuration_version,
                batch=batch,
                line_id=order.line_id,
                loss_category="DOWNTIME",
                loss_reason_code="MACHINE_DOWNTIME",
                loss_quantity=0.0,
                loss_duration_seconds=elapsed_seconds,
                quantity_uom=order.quantity_uom,
                machine_fault_event_id=machine_fault_event_id,
                scenario_id=scenario_id,
                scenario_instance_id=scenario_instance_id,
                notes="Line unavailable during execution window.",
            )
            events.append(loss)
        elif result.loss_category is not None and result.loss_reason_code is not None:
            expected = (
                max(line_snapshot.nominal_bottleneck_rate_units_min, 0.0)
                * elapsed_seconds
                / 60.0
            )
            slowdown_loss = max(0.0, expected - result.produced_quantity)
            if slowdown_loss > 0:
                events.append(
                    self.event_factory.build(
                        context.simulator_run_id,
                        order,
                        "ProductionLossRecorded",
                        context.current_time,
                        context.next_sequence(),
                        context.deterministic_seed,
                        context.configuration_version,
                        batch=batch,
                        line_id=order.line_id,
                        loss_category=result.loss_category,
                        loss_reason_code=result.loss_reason_code,
                        loss_quantity=slowdown_loss,
                        loss_duration_seconds=elapsed_seconds,
                        quantity_uom=order.quantity_uom,
                        machine_fault_event_id=machine_fault_event_id,
                        scenario_id=scenario_id,
                        scenario_instance_id=scenario_instance_id,
                        notes="Production rate below nominal bottleneck capacity.",
                    )
                )

        if batch.remaining_quantity <= 1e-9:
            batch.status = BatchStatus.COMPLETED
            batch.actual_end_time = context.current_time
            events.append(
                self.event_factory.build(
                    context.simulator_run_id,
                    order,
                    "BatchCompleted",
                    context.current_time,
                    context.next_sequence(),
                    context.deterministic_seed,
                    context.configuration_version,
                    batch=batch,
                    line_id=order.line_id,
                    actual_quantity=batch.actual_quantity,
                    good_quantity=batch.good_quantity,
                    rejected_quantity=batch.rejected_quantity,
                    quantity_uom=order.quantity_uom,
                    actual_end_time=batch.actual_end_time,
                    causation_id=events[-1].event_id if events else None,
                )
            )

        if order.remaining_quantity <= 1e-9 and all(
            current.status is BatchStatus.COMPLETED
            for current in getattr(order, "_batches", [])
        ):
            order.status = ProductionOrderStatus.COMPLETED
            order.actual_end_time = context.current_time
            events.append(
                self.event_factory.build(
                    context.simulator_run_id,
                    order,
                    "ProductionCompleted",
                    context.current_time,
                    context.next_sequence(),
                    context.deterministic_seed,
                    context.configuration_version,
                    actual_quantity=order.actual_quantity,
                    good_quantity=order.good_quantity,
                    rejected_quantity=order.rejected_quantity,
                    quantity_uom=order.quantity_uom,
                    actual_end_time=order.actual_end_time,
                    causation_id=events[-1].event_id if events else None,
                )
            )
        return events

    def attach_batches(
        self,
        order: ProductionOrder,
        batches: list[ProductionBatch],
    ) -> None:
        if sum(batch.planned_quantity for batch in batches) != order.planned_quantity:
            raise ValueError("Attached batches do not reconcile to order quantity")
        order._batches = batches

    def pause_batch(
        self,
        context: SimulationContext,
        order: ProductionOrder,
        batch: ProductionBatch,
        pause_reason_code: str,
        causation_id: str | None = None,
    ) -> ProductionEvent:
        if batch.status not in {BatchStatus.STARTED, BatchStatus.IN_PROGRESS}:
            raise ValueError("Only active batches can be paused")
        batch.status = BatchStatus.PAUSED
        batch.paused_at = context.current_time
        order.status = ProductionOrderStatus.PAUSED
        return self.event_factory.build(
            context.simulator_run_id,
            order,
            "ProductionPaused",
            context.current_time,
            context.next_sequence(),
            context.deterministic_seed,
            context.configuration_version,
            batch=batch,
            line_id=order.line_id,
            pause_reason_code=pause_reason_code,
            causation_id=causation_id,
            notes="Production paused by execution condition.",
        )

    def resume_batch(
        self,
        context: SimulationContext,
        order: ProductionOrder,
        batch: ProductionBatch,
        causation_id: str | None = None,
    ) -> ProductionEvent:
        if batch.status is not BatchStatus.PAUSED:
            raise ValueError("Only paused batches can be resumed")
        batch.status = BatchStatus.IN_PROGRESS
        order.status = ProductionOrderStatus.IN_PROGRESS
        return self.event_factory.build(
            context.simulator_run_id,
            order,
            "ProductionResumed",
            context.current_time,
            context.next_sequence(),
            context.deterministic_seed,
            context.configuration_version,
            batch=batch,
            line_id=order.line_id,
            actual_start_time=context.current_time,
            causation_id=causation_id,
        )

    @staticmethod
    def _require_order_status(
        order: ProductionOrder,
        allowed: set[ProductionOrderStatus],
    ) -> None:
        if order.status not in allowed:
            raise ValueError(
                f"Order {order.production_order_id} is {order.status}, expected {sorted(allowed)}"
            )
