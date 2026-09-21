from datetime import datetime, timezone, timedelta
from pathlib import Path
from uuid import UUID

from industrial_sim.engine.context import SimulationContext
from industrial_sim.production.catalog import load_production_catalog
from industrial_sim.production.engine import ProductionExecutionEngine
from industrial_sim.production.generator import GeneratedOrderPlan
from industrial_sim.simulation.step_engine import IntegratedSimulationStepEngine
from industrial_sim.world.machines import MachineWorldLoader

ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT / "data_reference" / "seed"
START = datetime(2026, 9, 21, 0, 30, tzinfo=timezone.utc)
RUN_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


def build_engine() -> IntegratedSimulationStepEngine:
    context = SimulationContext(
        simulator_run_id=RUN_ID,
        deterministic_seed=20260921,
        generator_version="0.1.0",
        configuration_version="1.0.0",
        current_time=START,
    )
    machines = MachineWorldLoader(
        DATA_ROOT / "machine_master_seed.csv"
    ).load()
    catalog = load_production_catalog(
        ROOT / "config" / "simulator_production.yaml",
        DATA_ROOT / "product_seed.csv",
        DATA_ROOT / "line_seed.csv",
    )
    production_engine = ProductionExecutionEngine.from_config(
        catalog,
        ROOT / "config" / "simulator_production.yaml",
        deterministic_seed=20260921,
        configuration_version="1.0.0",
    )
    return IntegratedSimulationStepEngine.from_repository_config(
        context=context,
        machines=machines,
        production_engine=production_engine,
        repository_root=ROOT,
    )


def production_plan() -> GeneratedOrderPlan:
    return GeneratedOrderPlan(
        production_order_id=UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
        plant_id="PLT-CHN-01",
        line_id="CHN-L01",
        product_id="PROD-HOUSING-E01",
        planned_quantity=10,
        planned_start_time=START,
        planned_end_time=START + timedelta(minutes=15),
        batch_count=1,
        production_sequence=1,
    )


def test_world_loads_exactly_270_machines() -> None:
    engine = build_engine()
    assert len(engine.machines) == 270
    assert len({runtime.machine.line_id for runtime in engine.machines.values()}) == 15


def test_normal_line_produces_after_30_second_aggregation_window() -> None:
    engine = build_engine()
    registration_events = engine.register_production_plan(production_plan())
    assert [event.event_type for event in registration_events] == [
        "ProductionOrderCreated",
        "ProductionOrderReleased",
        "ProductionStarted",
        "BatchStarted",
    ]

    results = [engine.step(5) for _ in range(6)]
    production_events = [
        event
        for result in results
        for event in result.production_events
    ]

    assert production_events
    assert any(event.event_type == "UnitProduced" for event in production_events)
    produced = next(event for event in production_events if event.event_type == "UnitProduced")
    assert produced.actual_quantity is not None
    assert produced.actual_quantity > 0
    assert produced.good_quantity + produced.rejected_quantity <= produced.actual_quantity + 1e-9


def test_scenario_failure_affects_state_telemetry_and_production() -> None:
    engine = build_engine()
    engine.register_production_plan(production_plan())
    scenario = engine.activate_scenario("CHN-L01-CNC01", "SCN-CNC-OVH")
    scenario.planned_end_at = START + timedelta(seconds=10)

    first = engine.step(5)
    assert any(
        event.event_type == "AlarmRaised"
        for event in first.operational_events
    )
    assert any(
        event.scenario_instance_id == str(scenario.scenario_instance_id)
        for event in first.telemetry_events
    )

    second = engine.step(5)
    operational_types = [event.event_type for event in second.operational_events]
    assert "MachineFaulted" in operational_types
    assert "StateChanged" in operational_types
    assert engine.machines["CHN-L01-CNC01"].machine.state.value == "FAULT"

    later_results = [engine.step(5) for _ in range(4)]
    production_events = [
        event
        for result in later_results
        for event in result.production_events
    ]
    losses = [
        event
        for event in production_events
        if event.event_type == "ProductionLossRecorded"
    ]
    assert losses
    downtime = next(event for event in losses if event.loss_category == "DOWNTIME")
    assert downtime.machine_fault_event_id is not None


def test_tick_generation_sequence_is_strictly_increasing() -> None:
    engine = build_engine()
    registration_events = engine.register_production_plan(production_plan())
    scenario = engine.activate_scenario("CHN-L01-CNC01", "SCN-CNC-OVH")
    results = [engine.step(5) for _ in range(6)]

    events = [
        *registration_events,
        *[event for result in results for event in result.operational_events],
        *[event for result in results for event in result.telemetry_events],
        *[event for result in results for event in result.production_events],
    ]
    sequences = sorted(
        [
            event.generation_sequence
            for event in events
            if event.generation_sequence is not None
        ]
        + [scenario.generation_sequence]
    )
    assert len(sequences) == len(set(sequences))
    assert sequences == list(range(1, len(sequences) + 1))
