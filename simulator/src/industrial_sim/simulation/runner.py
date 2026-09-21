from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import yaml

from industrial_sim.config.loader import load_generation_contract
from industrial_sim.domain.run import RunMode
from industrial_sim.engine.context import SimulationContext
from industrial_sim.production.catalog import load_production_catalog
from industrial_sim.production.engine import ProductionExecutionEngine
from industrial_sim.production.generator import EnterpriseProductionGenerator
from industrial_sim.simulation.output import PartitionedEventStreamWriter
from industrial_sim.simulation.step_engine import IntegratedSimulationStepEngine
from industrial_sim.world.machines import MachineWorldLoader


@dataclass(frozen=True)
class SimulationRunnerResult:
    run_id: UUID
    mode: RunMode
    simulation_start: datetime
    simulation_end: datetime
    tick_count: int
    order_count: int
    event_count: int
    output_manifest: str


class EnterpriseSimulationRunner:
    """Run the integrated simulator and stream all generated events to disk."""

    def __init__(self, repository_root: str | Path) -> None:
        self.root = Path(repository_root)
        self.generation_contract = load_generation_contract(
            self.root / "config" / "simulator_data_generation.yaml"
        )

    def run(
        self,
        mode: RunMode,
        start_time: datetime,
        end_time: datetime,
        seed: int | None = None,
        run_id: UUID | None = None,
        output_root: str | Path = "output/simulator",
    ) -> SimulationRunnerResult:
        if start_time.tzinfo is None or end_time.tzinfo is None:
            raise ValueError("Simulation times must be timezone-aware")
        if end_time <= start_time:
            raise ValueError("end_time must be after start_time")

        effective_seed = (
            self.generation_contract.default_seed if seed is None else seed
        )
        effective_run_id = run_id or UUID(
            "00000000-0000-0000-0000-000000000001"
        )

        context = SimulationContext(
            simulator_run_id=effective_run_id,
            deterministic_seed=effective_seed,
            generator_version="0.1.0",
            configuration_version=self.generation_contract.contract_version,
            current_time=start_time.astimezone(timezone.utc),
        )
        machines = MachineWorldLoader(
            self.root / "data_reference" / "seed" / "machine_master_seed.csv"
        ).load()
        catalog = load_production_catalog(
            self.root / "config" / "simulator_production.yaml",
            self.root / "data_reference" / "seed" / "product_seed.csv",
            self.root / "data_reference" / "seed" / "line_seed.csv",
        )
        production_engine = ProductionExecutionEngine.from_config(
            catalog,
            self.root / "config" / "simulator_production.yaml",
            deterministic_seed=effective_seed,
            configuration_version=self.generation_contract.contract_version,
        )
        step_engine = IntegratedSimulationStepEngine.from_repository_config(
            context=context,
            machines=machines,
            production_engine=production_engine,
            repository_root=self.root,
        )
        writer = PartitionedEventStreamWriter(output_root)

        generation = self.generation_contract.raw
        mode_config = generation["generation"]["modes"][mode.value]
        if mode is RunMode.LIVE:
            tick_seconds = int(generation["time"]["live_tick_seconds"])
        else:
            tick_seconds = int(generation["time"]["telemetry"]["baseline_interval_seconds"])

        generator = EnterpriseProductionGenerator(
            catalog=catalog,
            execution_engine=production_engine,
            orders_per_plant_per_day_range=tuple(
                generation["production_generation"]["orders_per_plant_per_day_range"]
            ),
            planned_quantity_range_units=tuple(
                generation["production_generation"]["quantity_range_units"]
            ),
            batch_count_range=tuple(
                generation["batch_generation"]["batch_count_range_per_order"]
            ),
        )
        plant_ids = ("PLT-CHN-01", "PLT-PUN-01", "PLT-CBE-01")

        plans = []
        cursor_day = start_time
        while cursor_day < end_time:
            plans.extend(generator.generate_day(context, cursor_day, plant_ids))
            cursor_day += timedelta(days=1)
        plans.sort(
            key=lambda plan: (
                plan.planned_start_time,
                plan.plant_id,
                plan.line_id,
                plan.production_sequence,
            )
        )

        plan_index = 0
        tick_count = 0
        order_count = 0
        cursor = start_time.astimezone(timezone.utc)

        while cursor < end_time:
            context.current_time = cursor
            due_plans = []
            while plan_index < len(plans) and plans[plan_index].planned_start_time <= cursor:
                due_plans.append(plans[plan_index])
                plan_index += 1

            for plan in due_plans:
                registration_events = step_engine.register_production_plan(plan)
                writer.write(registration_events)
                order_count += 1

            result = step_engine.step(tick_seconds)
            writer.write(result.operational_events)
            writer.write(result.telemetry_events)
            writer.write(result.production_events)

            tick_count += 1
            cursor = result.event_time

        manifest_path = writer.write_manifest()
        return SimulationRunnerResult(
            run_id=effective_run_id,
            mode=mode,
            simulation_start=start_time,
            simulation_end=end_time,
            tick_count=tick_count,
            order_count=order_count,
            event_count=writer.manifest()["total_event_count"],
            output_manifest=str(manifest_path),
        )
