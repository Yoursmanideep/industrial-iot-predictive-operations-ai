from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import yaml

from industrial_sim.context.production_context import ProductionContextEngine
from industrial_sim.production.batch_writer import EventBatchManifest, PartitionedProductionEventWriter
from industrial_sim.production.catalog import load_production_catalog
from industrial_sim.production.engine import ProductionExecutionEngine
from industrial_sim.engine.context import SimulationContext
from industrial_sim.production.generator import EnterpriseProductionGenerator


@dataclass(frozen=True)
class EnterpriseGenerationResult:
    run_id: UUID
    simulation_start: datetime
    simulation_end: datetime
    order_count: int
    batch_count: int
    event_count: int
    event_manifest: EventBatchManifest


def generate_production_plan(
    run_id: UUID,
    deterministic_seed: int,
    start_time: datetime,
    end_time: datetime,
    configuration_version: str = "1.0.0",
    output_root: str | Path = "output/production",
) -> EnterpriseGenerationResult:
    if end_time <= start_time:
        raise ValueError("end_time must be after start_time")
    if start_time.tzinfo is None or end_time.tzinfo is None:
        raise ValueError("start_time and end_time must be timezone-aware")

    config_root = Path(__file__).resolve().parents[4] / "config"
    data_root = Path(__file__).resolve().parents[4] / "data_reference" / "seed"
    production_config = yaml.safe_load(
        (config_root / "simulator_production.yaml").read_text(encoding="utf-8")
    )
    generation_config = yaml.safe_load(
        (config_root / "simulator_data_generation.yaml").read_text(encoding="utf-8")
    )

    catalog = load_production_catalog(
        config_root / "simulator_production.yaml",
        data_root / "product_seed.csv",
        data_root / "line_seed.csv",
    )
    context = SimulationContext(
        simulator_run_id=run_id,
        deterministic_seed=deterministic_seed,
        generator_version="0.1.0",
        configuration_version=configuration_version,
        current_time=start_time,
    )
    execution_engine = ProductionExecutionEngine.from_config(
        catalog,
        config_root / "simulator_production.yaml",
        deterministic_seed=deterministic_seed,
        configuration_version=configuration_version,
    )

    generator = EnterpriseProductionGenerator(
        catalog=catalog,
        execution_engine=execution_engine,
        orders_per_plant_per_day_range=tuple(
            generation_config["production_generation"]["orders_per_plant_per_day_range"]
        ),
        planned_quantity_range_units=tuple(
            generation_config["production_generation"]["quantity_range_units"]
        ),
        batch_count_range=tuple(
            generation_config["batch_generation"]["batch_count_range_per_order"]
        ),
    )

    plant_ids = ("PLT-CHN-01", "PLT-PUN-01", "PLT-CBE-01")
    all_events = []
    all_batches = 0
    all_orders = 0
    cursor = start_time
    while cursor < end_time:
        plans = sorted(
            generator.generate_day(context, cursor, plant_ids),
            key=lambda plan: (plan.planned_start_time, plan.plant_id, plan.line_id, plan.production_sequence),
        )
        all_orders += len(plans)
        for plan in plans:
            context.current_time = plan.planned_start_time
            order, batches, events = generator.instantiate(context, plan)
            all_batches += len(batches)
            events.append(execution_engine.release_order(context, order))
            events.append(execution_engine.start_order(context, order))
            batch_cursor = plan.planned_start_time
            cycle_seconds = generator.catalog.product(plan.product_id).standard_cycle_time_seconds
            for batch in batches:
                context.current_time = batch_cursor
                events.extend(execution_engine.start_batch(context, order, batch))
                batch_cursor += timedelta(
                    seconds=max(1.0, batch.planned_quantity * cycle_seconds / 0.82)
                )
            all_events.extend(events)
        cursor += timedelta(days=1)

    writer = PartitionedProductionEventWriter(output_root)
    manifest = writer.write(all_events)
    return EnterpriseGenerationResult(
        run_id=run_id,
        simulation_start=start_time,
        simulation_end=end_time,
        order_count=all_orders,
        batch_count=all_batches,
        event_count=manifest.event_count,
        event_manifest=manifest,
    )
