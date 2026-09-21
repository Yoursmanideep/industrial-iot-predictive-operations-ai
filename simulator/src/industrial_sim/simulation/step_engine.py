from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import yaml

from industrial_sim.context.environment import EnvironmentModel
from industrial_sim.context.production_context import ProductionContextEngine
from industrial_sim.context.shift import ShiftResolver
from industrial_sim.context.workload import WorkloadInputs, WorkloadModel
from industrial_sim.domain.machine import MachineState
from industrial_sim.domain.scenario import ScenarioInstance, ScenarioStage, ScenarioStatus
from industrial_sim.engine.context import SimulationContext
from industrial_sim.events.operational import OperationalEventFactory
from industrial_sim.machines.base import MachineBehaviorContext
from industrial_sim.machines.profiles import load_machine_profiles
from industrial_sim.machines.registry import MachineBehaviorRegistry
from industrial_sim.machines.state_machine import MachineStateMachine
from industrial_sim.production.engine import ProductionExecutionEngine
from industrial_sim.production.events import ProductionEvent
from industrial_sim.production.generator import GeneratedOrderPlan
from industrial_sim.scenarios.catalog import ScenarioCatalog, load_scenario_catalog
from industrial_sim.scenarios.engine import ScenarioEngine
from industrial_sim.scenarios.event_engine import ScenarioOperationalEventEngine
from industrial_sim.scenarios.telemetry import ScenarioAwareTelemetryEngine
from industrial_sim.telemetry.events import MachineTelemetryEvent, TelemetryEventFactory
from industrial_sim.world.machines import MachineRuntime


@dataclass
class ActiveProductionLine:
    order: object
    batches: list[object]
    active_batch_index: int = 0
    accumulated_seconds: float = 0.0

    @property
    def active_batch(self):
        if self.active_batch_index >= len(self.batches):
            return None
        return self.batches[self.active_batch_index]


@dataclass(frozen=True)
class SimulationTickResult:
    event_time: datetime
    telemetry_events: tuple[MachineTelemetryEvent, ...]
    operational_events: tuple[object, ...]
    production_events: tuple[ProductionEvent, ...]
    total_events: int


class IntegratedSimulationStepEngine:
    """Synchronize machine, scenario, telemetry and production on one simulation clock."""

    def __init__(
        self,
        context: SimulationContext,
        machines: dict[str, MachineRuntime],
        production_engine: ProductionExecutionEngine,
        production_context_engine: ProductionContextEngine,
        behavior_registry: MachineBehaviorRegistry,
        scenario_engine: ScenarioEngine,
        telemetry_engine: ScenarioAwareTelemetryEngine,
        operational_event_engine: ScenarioOperationalEventEngine,
        machine_state_machine: MachineStateMachine | None = None,
        production_aggregation_seconds: int = 30,
        baseline_telemetry_interval_seconds: int = 5,
        incident_telemetry_interval_seconds: int = 5,
    ) -> None:
        if production_aggregation_seconds <= 0:
            raise ValueError("production_aggregation_seconds must be positive")
        self.context = context
        self.machines = machines
        self.production_engine = production_engine
        self.production_context_engine = production_context_engine
        self.behavior_registry = behavior_registry
        self.scenario_engine = scenario_engine
        self.telemetry_engine = telemetry_engine
        self.operational_event_engine = operational_event_engine
        self.machine_state_machine = machine_state_machine or MachineStateMachine()
        if baseline_telemetry_interval_seconds <= 0 or incident_telemetry_interval_seconds <= 0:
            raise ValueError("Telemetry intervals must be positive")
        self.production_aggregation_seconds = production_aggregation_seconds
        self.baseline_telemetry_interval_seconds = baseline_telemetry_interval_seconds
        self.incident_telemetry_interval_seconds = incident_telemetry_interval_seconds
        self._telemetry_elapsed_seconds = 0
        self._active_scenarios: dict[str, ScenarioInstance] = {}
        self._active_production_lines: dict[str, ActiveProductionLine] = {}
        self._latest_fault_event_by_machine: dict[str, str] = {}
        self._telemetry_factory = TelemetryEventFactory()

    @classmethod
    def from_repository_config(
        cls,
        context: SimulationContext,
        machines: dict[str, MachineRuntime],
        production_engine: ProductionExecutionEngine,
        repository_root: str | Path,
    ) -> "IntegratedSimulationStepEngine":
        root = Path(repository_root)
        context_config = yaml.safe_load(
            (root / "config" / "simulator_context.yaml").read_text(encoding="utf-8")
        )
        profiles = load_machine_profiles(
            root / "config" / "simulator_machine_profiles.yaml"
        )
        scenario_catalog: ScenarioCatalog = load_scenario_catalog(
            root / "config" / "scenario_catalog.yaml"
        )
        environment = EnvironmentModel(context_config)
        shifts = ShiftResolver(context_config)
        workload = WorkloadModel(context_config)
        production_context_engine = ProductionContextEngine(
            environment,
            shifts,
            workload,
        )
        behavior_registry = MachineBehaviorRegistry.with_generic_profiles(profiles)
        scenario_engine = ScenarioEngine(scenario_catalog)
        telemetry_engine = ScenarioAwareTelemetryEngine.from_catalog(scenario_catalog)
        operational_event_engine = ScenarioOperationalEventEngine.from_config(
            simulator_run_id=context.simulator_run_id,
            deterministic_seed=context.deterministic_seed,
            configuration_version=context.configuration_version,
            mapping_path=root / "config" / "simulator_alarm_mapping.yaml",
            event_factory=OperationalEventFactory(),
        )
        generation_config = yaml.safe_load(
            (root / "config" / "simulator_data_generation.yaml").read_text(
                encoding="utf-8"
            )
        )
        aggregation = int(
            generation_config["time"]["production"]["unit_produced_aggregation_seconds"]
        )
        return cls(
            context=context,
            machines=machines,
            production_engine=production_engine,
            production_context_engine=production_context_engine,
            behavior_registry=behavior_registry,
            scenario_engine=scenario_engine,
            telemetry_engine=telemetry_engine,
            operational_event_engine=operational_event_engine,
            production_aggregation_seconds=aggregation,
            baseline_telemetry_interval_seconds=int(
                generation_config["time"]["telemetry"]["baseline_interval_seconds"]
            ),
            incident_telemetry_interval_seconds=int(
                generation_config["time"]["telemetry"]["incident_interval_seconds"]
            ),
        )

    def register_production_plan(
        self,
        plan: GeneratedOrderPlan,
    ) -> tuple[ProductionEvent, ...]:
        planned_start = plan.planned_start_time.astimezone(timezone.utc)
        if self.context.current_time < planned_start:
            self.context.current_time = planned_start
        order, batches, created = self._instantiate_plan(plan)
        events: list[ProductionEvent] = list(created)
        events.append(self.production_engine.release_order(self.context, order))
        events.append(self.production_engine.start_order(self.context, order))
        if batches:
            events.extend(
                self.production_engine.start_batch(
                    self.context,
                    order,
                    batches[0],
                    operation_sequence=1,
                )
            )
        self._active_production_lines[plan.line_id] = ActiveProductionLine(
            order=order,
            batches=batches,
        )
        return tuple(events)

    def activate_scenario(
        self,
        machine_id: str,
        scenario_id: str,
    ) -> ScenarioInstance:
        runtime = self._runtime(machine_id)
        instance = self.scenario_engine.create_instance(
            simulator_run_id=self.context.simulator_run_id,
            machine_id=machine_id,
            scenario_id=scenario_id,
            started_at=self.context.current_time,
            generation_sequence=self.context.next_sequence(),
            correlation_id=None,
        )
        runtime.machine.active_scenario_instance_id = str(
            instance.scenario_instance_id
        )
        self._active_scenarios[machine_id] = instance
        return instance

    def step(self, seconds: int = 5) -> SimulationTickResult:
        if seconds <= 0:
            raise ValueError("seconds must be positive")
        self.context.current_time = (
            self.context.current_time.astimezone(timezone.utc)
        )
        self.context.current_time = self.context.current_time.replace(
            microsecond=0
        )
        from datetime import timedelta

        self.context.current_time += timedelta(seconds=seconds)
        current_time = self.context.current_time

        operational_events = self._advance_scenarios(current_time)
        self._telemetry_elapsed_seconds += seconds
        telemetry_interval = (
            self.incident_telemetry_interval_seconds
            if self._active_scenarios
            else self.baseline_telemetry_interval_seconds
        )
        telemetry_due = self._telemetry_elapsed_seconds >= telemetry_interval
        telemetry_events = (
            self._generate_machine_telemetry(current_time)
            if telemetry_due
            else []
        )
        if telemetry_due:
            self._telemetry_elapsed_seconds = 0

        production_events: list[ProductionEvent] = []
        for line_id, execution in list(self._active_production_lines.items()):
            execution.accumulated_seconds += seconds
            if execution.accumulated_seconds < self.production_aggregation_seconds:
                continue

            elapsed = execution.accumulated_seconds
            execution.accumulated_seconds = 0.0
            production_events.extend(
                self._execute_line(line_id, execution, elapsed, current_time)
            )

        self._cleanup_terminal_scenarios()
        return SimulationTickResult(
            event_time=current_time,
            telemetry_events=tuple(telemetry_events),
            operational_events=tuple(operational_events),
            production_events=tuple(production_events),
            total_events=(
                len(telemetry_events)
                + len(operational_events)
                + len(production_events)
            ),
        )

    def _advance_scenarios(self, current_time: datetime) -> list[object]:
        events: list[object] = []
        for machine_id, instance in list(self._active_scenarios.items()):
            progress, transition = self.scenario_engine.advance(instance, current_time)
            if transition is None:
                continue

            runtime = self._runtime(machine_id)
            machine = runtime.machine
            previous_state = machine.state.value

            generated = self.operational_event_engine.transition_events(
                machine=machine,
                transition=transition,
                scenario_id=instance.scenario_id,
                scenario_instance_id=str(instance.scenario_instance_id),
                failure_mode_code=instance.failure_mode_code,
                affected_signals=self.scenario_engine.catalog.get(
                    instance.scenario_id
                ).affected_signals,
                correlation_id=instance.correlation_id,
                generation_sequence_start=self.context.next_sequence(),
                current_state=previous_state,
                intervention_event_id=instance.intervention_event_id,
            )
            if generated:
                self.context.generation_sequence += len(generated) - 1
                events.extend(generated)
                for generated_event in generated:
                    if getattr(generated_event, "event_type", None) == "MachineFaulted":
                        self._latest_fault_event_by_machine[machine_id] = generated_event.event_id

            if progress.stage is ScenarioStage.FAILURE:
                if machine.state is not MachineState.FAULT:
                    self.machine_state_machine.transition(
                        machine,
                        MachineState.FAULT,
                        current_time,
                        "SCENARIO_FAILURE",
                    )
            elif progress.stage is ScenarioStage.MAINTENANCE:
                if machine.state is not MachineState.MAINTENANCE:
                    if machine.state is MachineState.FAULT:
                        self.machine_state_machine.transition(
                            machine,
                            MachineState.MAINTENANCE,
                            current_time,
                            "SCENARIO_MAINTENANCE",
                        )
                    elif machine.state is MachineState.RUNNING:
                        self.machine_state_machine.transition(
                            machine,
                            MachineState.MAINTENANCE,
                            current_time,
                            "SCENARIO_MAINTENANCE",
                        )
            elif progress.stage is ScenarioStage.RECOVERY:
                if machine.state is not MachineState.RECOVERY:
                    if machine.state is MachineState.MAINTENANCE:
                        self.machine_state_machine.transition(
                            machine,
                            MachineState.RECOVERY,
                            current_time,
                            "SCENARIO_RECOVERY",
                        )
        return events

    def _generate_machine_telemetry(
        self,
        current_time: datetime,
    ) -> list[MachineTelemetryEvent]:
        result: list[MachineTelemetryEvent] = []
        for machine_id in sorted(self.machines):
            runtime = self.machines[machine_id]
            machine = runtime.machine
            scenario = self._active_scenarios.get(machine_id)
            scenario_progress = None
            if scenario is not None:
                scenario_progress, _ = self.scenario_engine.advance(
                    scenario,
                    current_time,
                )

            product_id, cycle_seconds = self._product_context_for_line(machine.line_id)
            health_factor = 1.0
            if scenario_progress is not None:
                health_factor = max(0.40, 1.0 - 0.60 * scenario_progress.severity)
            age_years = max(
                0.0,
                (current_time.date() - runtime.installation_date).days / 365.25,
            )
            production_context = self.production_context_engine.build(
                plant_id=machine.plant_id,
                line_id=machine.line_id,
                event_time_utc=current_time,
                inputs=WorkloadInputs(
                    rated_capacity_units_min=runtime.rated_capacity_units_min,
                    product_cycle_time_seconds=cycle_seconds,
                    machine_health_factor=health_factor,
                    machine_age_years=age_years,
                    state=machine.state.value,
                ),
                product_id=product_id,
                product_cycle_time_seconds=cycle_seconds,
            )
            behavior_context = MachineBehaviorContext(
                simulation_seconds=current_time.timestamp(),
                workload_factor=production_context.workload.workload_factor,
                ambient_temperature_c=production_context.ambient_temperature_c,
                health_factor=health_factor,
                scenario_stage=(
                    scenario_progress.stage.value
                    if scenario_progress is not None
                    else None
                ),
                scenario_severity=(
                    scenario_progress.severity
                    if scenario_progress is not None
                    else 0.0
                ),
                event_time=current_time,
            )
            signals = self.telemetry_engine.generate(
                machine=machine,
                behavior_context=behavior_context,
                scenario_instance=scenario,
                scenario_progress=scenario_progress,
                event_time=current_time,
            )
            result.append(
                self._telemetry_factory.build(
                    run_id=self.context.simulator_run_id,
                    machine=machine,
                    event_time=current_time,
                    generation_sequence=self.context.next_sequence(),
                    seed=self.context.deterministic_seed,
                    configuration_version=self.context.configuration_version,
                    signals=signals,
                    scenario_id=scenario.scenario_id if scenario else None,
                    scenario_instance_id=(
                        str(scenario.scenario_instance_id) if scenario else None
                    ),
                )
            )
        return result

    def _execute_line(
        self,
        line_id: str,
        execution: ActiveProductionLine,
        elapsed_seconds: float,
        current_time: datetime,
    ) -> list[ProductionEvent]:
        batch = execution.active_batch
        if batch is None:
            self._active_production_lines.pop(line_id, None)
            return []

        product = self.production_engine.catalog.product(batch.product_id)
        route_machine_ids = self.production_engine.catalog.route_machine_ids(
            line_id,
            batch.product_id,
        )
        machine_inputs: list[object] = []
        scenario_quality_multiplier = 1.0
        scenario_instance_id = None
        scenario_id = None
        fault_event_id = None

        for machine_id in route_machine_ids:
            runtime = self._runtime(machine_id)
            scenario = self._active_scenarios.get(machine_id)
            scenario_progress = None
            if scenario is not None:
                scenario_progress, _ = self.scenario_engine.advance(
                    scenario,
                    current_time,
                )
                scenario_id = scenario.scenario_id
                scenario_instance_id = str(scenario.scenario_instance_id)
                scenario_quality_multiplier *= scenario_progress.quality_multiplier
                fault_event_id = (
                    fault_event_id
                    or self._latest_fault_event_by_machine.get(machine_id)
                )
            product_context = self.production_context_engine.build(
                plant_id=runtime.machine.plant_id,
                line_id=line_id,
                event_time_utc=current_time,
                inputs=WorkloadInputs(
                    rated_capacity_units_min=runtime.rated_capacity_units_min,
                    product_cycle_time_seconds=product.standard_cycle_time_seconds,
                    machine_health_factor=(
                        max(0.40, 1.0 - 0.60 * scenario_progress.severity)
                        if scenario_progress is not None
                        else 1.0
                    ),
                    machine_age_years=max(
                        0.0,
                        (
                            current_time.date() - runtime.installation_date
                        ).days
                        / 365.25,
                    ),
                    state=runtime.machine.state.value,
                ),
                product_id=batch.product_id,
                product_cycle_time_seconds=product.standard_cycle_time_seconds,
            )
            eligible = runtime.machine.state is MachineState.RUNNING
            multiplier = (
                scenario_progress.production_multiplier
                if scenario_progress is not None
                else 1.0
            )
            machine_inputs.append(
                MachineExecutionInput(
                    machine_id=machine_id,
                    machine_type=runtime.machine.machine_type,
                    effective_capacity_units_min=product_context.workload.effective_capacity_units_min,
                    available=eligible and product_context.workload.effective_capacity_units_min > 0,
                    scenario_production_multiplier=multiplier,
                    quality_multiplier=(
                        scenario_progress.quality_multiplier
                        if scenario_progress is not None
                        else 1.0
                    ),
                )
            )

        snapshot = self.production_engine.line_engine.snapshot(
            line_id=line_id,
            event_time=current_time,
            machines=tuple(machine_inputs),
        )
        events = self.production_engine.advance_batch(
            context=self.context,
            order=execution.order,
            batch=batch,
            line_snapshot=snapshot,
            production_context=self.production_context_engine.build(
                plant_id=execution.order.plant_id,
                line_id=line_id,
                event_time_utc=current_time,
                inputs=WorkloadInputs(
                    rated_capacity_units_min=max(
                        snapshot.bottleneck_rate_units_min,
                        0.01,
                    ),
                    product_cycle_time_seconds=product.standard_cycle_time_seconds,
                    machine_health_factor=1.0,
                    machine_age_years=0.0,
                    state="RUNNING",
                ),
                product_id=batch.product_id,
                product_cycle_time_seconds=product.standard_cycle_time_seconds,
            ),
            elapsed_seconds=elapsed_seconds,
            scenario_quality_multiplier=scenario_quality_multiplier,
            machine_fault_event_id=fault_event_id,
            scenario_id=scenario_id,
            scenario_instance_id=scenario_instance_id,
        )

        if batch.status.value == "COMPLETED":
            execution.active_batch_index += 1
            next_batch = execution.active_batch
            if next_batch is not None:
                events.extend(
                    self.production_engine.start_batch(
                        self.context,
                        execution.order,
                        next_batch,
                        operation_sequence=next_batch.batch_sequence,
                    )
                )
            else:
                self._active_production_lines.pop(line_id, None)
        return events

    def _cleanup_terminal_scenarios(self) -> None:
        for machine_id, instance in list(self._active_scenarios.items()):
            if instance.status in {
                ScenarioStatus.FAILED,
                ScenarioStatus.AVOIDED,
                ScenarioStatus.RESOLVED,
            }:
                self._active_scenarios.pop(machine_id, None)
                self._runtime(machine_id).machine.active_scenario_instance_id = None

    def _instantiate_plan(self, plan: GeneratedOrderPlan):
        order, batches, events = self._production_generator().instantiate(
            self.context,
            plan,
        )
        return order, batches, events

    def _production_generator(self):
        from industrial_sim.production.generator import EnterpriseProductionGenerator
        from pathlib import Path

        root = Path(__file__).resolve().parents[4]
        document = yaml.safe_load(
            (root / "config" / "simulator_data_generation.yaml").read_text(
                encoding="utf-8"
            )
        )
        return EnterpriseProductionGenerator(
            catalog=self.production_engine.catalog,
            execution_engine=self.production_engine,
            orders_per_plant_per_day_range=tuple(
                document["production_generation"]["orders_per_plant_per_day_range"]
            ),
            planned_quantity_range_units=tuple(
                document["production_generation"]["quantity_range_units"]
            ),
            batch_count_range=tuple(
                document["batch_generation"]["batch_count_range_per_order"]
            ),
        )

    def _product_context_for_line(self, line_id: str):
        execution = self._active_production_lines.get(line_id)
        if execution is None or execution.active_batch is None:
            return None, 60.0
        batch = execution.active_batch
        product = self.production_engine.catalog.product(batch.product_id)
        return batch.product_id, product.standard_cycle_time_seconds

    def _runtime(self, machine_id: str) -> MachineRuntime:
        try:
            return self.machines[machine_id]
        except KeyError as exc:
            raise KeyError(f"Unknown machine_id: {machine_id}") from exc
