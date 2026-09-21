from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid5

import yaml

from industrial_sim.config.loader import load_generation_contract
from industrial_sim.domain.run import RunMode
from industrial_sim.engine.context import SimulationContext
from industrial_sim.production.catalog import load_production_catalog
from industrial_sim.production.engine import ProductionExecutionEngine
from industrial_sim.production.generator import EnterpriseProductionGenerator
from industrial_sim.validation.stream import ValidatedEventStreamWriter
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
    valid_event_count: int
    quarantined_event_count: int
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
        effective_run_id = run_id or uuid5(
            UUID("c0a80101-0000-0000-0000-000000000001"),
            "|".join(
                (
                    "simulation-run",
                    mode.value,
                    str(effective_seed),
                    start_time.astimezone(timezone.utc).isoformat(),
                    end_time.astimezone(timezone.utc).isoformat(),
                )
            ),
        )

        generation = self.generation_contract.raw

        context = SimulationContext(
            simulator_run_id=effective_run_id,
            deterministic_seed=effective_seed,
            generator_version="0.1.0",
            configuration_version=self.generation_contract.contract_version,
            current_time=start_time.astimezone(timezone.utc),
        )
        bootstrap_distribution = None
        if mode is RunMode.BOOTSTRAP:
            bootstrap_distribution = generation["bootstrap"]["machine_history"]["initial_state_distribution"]
        machines = MachineWorldLoader(
            self.root / "data_reference" / "seed" / "machine_master_seed.csv"
        ).load(
            initial_state_distribution=bootstrap_distribution,
            deterministic_seed=effective_seed,
        )
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
        if mode is RunMode.LIVE:
            baseline_telemetry_interval = int(
                generation["time"]["live_tick_seconds"]
            )
        else:
            baseline_telemetry_interval = int(
                generation["time"]["telemetry"]["baseline_interval_seconds"]
            )

        step_engine = IntegratedSimulationStepEngine.from_repository_config(
            context=context,
            machines=machines,
            production_engine=production_engine,
            repository_root=self.root,
            baseline_telemetry_interval_seconds=baseline_telemetry_interval,
            incident_telemetry_interval_seconds=int(
                generation["time"]["telemetry"]["incident_interval_seconds"]
            ),
        )
        writer = ValidatedEventStreamWriter(
            schema_root=self.root / "schemas",
            output_root=output_root,
        )

        tick_seconds = (
            int(generation["time"]["live_tick_seconds"])
            if mode is RunMode.LIVE
            else int(generation["time"]["telemetry"]["baseline_interval_seconds"])
        )

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
            if plan_index < len(plans) and plans[plan_index].planned_start_time > cursor:
                next_order_time = plans[plan_index].planned_start_time
                if next_order_time < cursor + timedelta(seconds=tick_seconds):
                    cursor = next_order_time
                    context.current_time = cursor

            while plan_index < len(plans) and plans[plan_index].planned_start_time <= cursor:
                registration_events = step_engine.register_production_plan(plans[plan_index])
                writer.write(registration_events)
                order_count += 1
                plan_index += 1

            step_end = min(end_time, cursor + timedelta(seconds=tick_seconds))
            step_seconds = max(1, int((step_end - cursor).total_seconds()))
            result = step_engine.step(step_seconds)
            writer.write(result.operational_events)
            writer.write(result.telemetry_events)
            writer.write(result.production_events)

            tick_count += 1
            cursor = result.event_time

        writer.close()
        manifest_path = writer.write_manifest()
        stream_manifest = writer.manifest()
        run_manifest_path = Path(manifest_path).with_name("simulation_run_manifest.json")
        run_manifest_path.write_text(
            json.dumps(
                {
                    "simulator_run_id": f"RUN-{effective_run_id}",
                    "run_mode": mode.value,
                    "deterministic_seed": effective_seed,
                    "configuration_version": self.generation_contract.contract_version,
                    "simulation_start": start_time.astimezone(timezone.utc).isoformat(),
                    "simulation_end": end_time.astimezone(timezone.utc).isoformat(),
                    "tick_count": tick_count,
                    "order_count": order_count,
                    "event_count": stream_manifest["validation"]["total_count"],
                    "valid_event_count": stream_manifest["validation"]["valid_count"],
                    "quarantined_event_count": stream_manifest["validation"]["quarantined_count"],
                    "event_manifest": str(
                        Path(manifest_path).with_name("run_event_manifest.json")
                    ),
                    "validation_manifest": str(manifest_path),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return SimulationRunnerResult(
            run_id=effective_run_id,
            mode=mode,
            simulation_start=start_time,
            simulation_end=end_time,
            tick_count=tick_count,
            order_count=order_count,
            event_count=stream_manifest["validation"]["total_count"],
            valid_event_count=stream_manifest["validation"]["valid_count"],
            quarantined_event_count=stream_manifest["validation"]["quarantined_count"],
            output_manifest=str(run_manifest_path),
        )
