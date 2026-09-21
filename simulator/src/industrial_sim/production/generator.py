from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from industrial_sim.engine.context import SimulationContext
from industrial_sim.production.catalog import ProductionCatalog
from industrial_sim.production.engine import ProductionExecutionEngine
from industrial_sim.production.identity import deterministic_production_order_id


@dataclass(frozen=True)
class GeneratedOrderPlan:
    production_order_id: UUID
    plant_id: str
    line_id: str
    product_id: str
    planned_quantity: int
    planned_start_time: datetime
    planned_end_time: datetime
    batch_count: int
    production_sequence: int


class EnterpriseProductionGenerator:
    """Deterministically generate an enterprise-scale production order plan."""

    def __init__(
        self,
        catalog: ProductionCatalog,
        execution_engine: ProductionExecutionEngine,
        orders_per_plant_per_day_range: tuple[int, int] = (30, 60),
        planned_quantity_range_units: tuple[int, int] = (100, 2500),
        batch_count_range: tuple[int, int] = (1, 8),
    ) -> None:
        low, high = orders_per_plant_per_day_range
        if low <= 0 or high < low:
            raise ValueError("Invalid orders_per_plant_per_day_range")
        q_low, q_high = planned_quantity_range_units
        if q_low <= 0 or q_high < q_low:
            raise ValueError("Invalid planned_quantity_range_units")
        b_low, b_high = batch_count_range
        if b_low <= 0 or b_high < b_low:
            raise ValueError("Invalid batch_count_range")

        self.catalog = catalog
        self.execution_engine = execution_engine
        self.orders_range = (low, high)
        self.quantity_range = (q_low, q_high)
        self.batch_range = (b_low, b_high)

    def generate_day(
        self,
        context: SimulationContext,
        date_time: datetime,
        plant_ids: tuple[str, ...],
    ) -> tuple[GeneratedOrderPlan, ...]:
        day_utc = date_time.astimezone(timezone.utc).date()
        plans: list[GeneratedOrderPlan] = []

        for plant_index, plant_id in enumerate(sorted(plant_ids)):
            rng = self._rng(context.deterministic_seed, "orders", plant_id, day_utc.isoformat())
            order_count = rng.randint(*self.orders_range)
            plant_lines = tuple(
                line_id for line_id in self.catalog.lines
                if line_id.startswith(plant_id[4:7] + "-")
            )
            if len(plant_lines) != 5:
                raise ValueError(f"Plant {plant_id} must map to exactly five lines")
            next_available: dict[str, datetime] = {
                line_id: datetime.combine(
                    day_utc,
                    datetime.min.time(),
                    tzinfo=timezone.utc,
                )
                + timedelta(hours=6)
                for line_id in plant_lines
            }

            for sequence in range(1, order_count + 1):
                product_id = self._select_product(rng)
                line_id = self._select_line(product_id, next_available, plant_lines)
                quantity = rng.randint(*self.quantity_range)
                batch_count = min(
                    rng.randint(*self.batch_range),
                    max(1, quantity),
                )

                start = max(
                    next_available[line_id],
                    datetime.combine(
                        day_utc,
                        datetime.min.time(),
                        tzinfo=timezone.utc,
                    ) + timedelta(minutes=rng.randint(0, 60)),
                )
                product = self.catalog.product(product_id)
                duration_seconds = max(
                    900.0,
                    quantity * product.standard_cycle_time_seconds / 0.82,
                )
                end = start + timedelta(seconds=duration_seconds)

                order_id = deterministic_production_order_id(
                    context.simulator_run_id,
                    plant_id,
                    line_id,
                    start,
                    sequence,
                )
                next_available[line_id] = end + timedelta(minutes=rng.randint(5, 20))
                plans.append(
                    GeneratedOrderPlan(
                        production_order_id=order_id,
                        plant_id=plant_id,
                        line_id=line_id,
                        product_id=product_id,
                        planned_quantity=quantity,
                        planned_start_time=start,
                        planned_end_time=end,
                        batch_count=batch_count,
                    production_sequence=sequence,
                    )
                )
        return tuple(plans)

    def instantiate(
        self,
        context: SimulationContext,
        plan: GeneratedOrderPlan,
    ):
        order, events = self.execution_engine.create_order(
            context=context,
            plant_id=plan.plant_id,
            line_id=plan.line_id,
            product_id=plan.product_id,
            planned_quantity=plan.planned_quantity,
            planned_start_time=plan.planned_start_time,
            production_sequence=plan.production_sequence,
        )
        batches = self.execution_engine.create_batches(
            context=context,
            order=order,
            batch_count=plan.batch_count,
        )
        self.execution_engine.attach_batches(order, batches)
        return order, batches, events

    def _select_product(self, rng: random.Random) -> str:
        products = sorted(self.catalog.products.values(), key=lambda p: p.product_id)
        weights = [self._product_weight(product.product_family) for product in products]
        return rng.choices(
            [product.product_id for product in products],
            weights=weights,
            k=1,
        )[0]

    @staticmethod
    def _product_weight(product_family: str) -> float:
        return {
            "Motor Assemblies": 1.20,
            "Pump Systems": 1.00,
            "Drive Systems": 1.00,
            "Fluid Control": 1.10,
            "Machined Components": 1.25,
            "Drive Components": 1.15,
        }.get(product_family, 1.0)

    def _select_line(
        self,
        product_id: str,
        next_available: dict[str, datetime],
        plant_lines: tuple[str, ...],
    ) -> str:
        route = self.catalog.product(product_id).route
        candidates = [
            line_id
            for line_id in self.catalog.lines
            if all(
                machine_type in self.catalog.machines_by_line_type[line_id]
                for machine_type in route
            )
        ]
        if not candidates:
            raise ValueError(f"No executable line found for {product_id}")
        return min(
            candidates,
            key=lambda line_id: (next_available[line_id], line_id),
        )

    @staticmethod
    def _rng(seed: int, *parts: str) -> random.Random:
        payload = "|".join((str(seed), *parts)).encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        return random.Random(int(digest[:16], 16))
