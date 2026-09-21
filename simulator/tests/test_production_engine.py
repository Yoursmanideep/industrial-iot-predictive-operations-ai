from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import yaml

from industrial_sim.context.environment import EnvironmentModel
from industrial_sim.context.production_context import ProductionContextEngine
from industrial_sim.context.shift import ShiftResolver
from industrial_sim.context.workload import WorkloadInputs, WorkloadModel
from industrial_sim.domain.production import BatchStatus, ProductionOrderStatus
from industrial_sim.engine.context import SimulationContext
from industrial_sim.production.catalog import load_production_catalog
from industrial_sim.production.engine import ProductionExecutionEngine
from industrial_sim.production.events import ProductionEventFactory
from industrial_sim.production.line_engine import LineCapacitySnapshot, LineExecutionEngine, MachineExecutionInput

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data_reference" / "seed"
RUN_ID = UUID("12345678-1234-5678-1234-567812345678")
START = datetime(2026, 9, 21, 6, 0, tzinfo=timezone.utc)


def context() -> SimulationContext:
    return SimulationContext(
        simulator_run_id=RUN_ID,
        deterministic_seed=20260921,
        generator_version="0.1.0",
        configuration_version="1.0.0",
        current_time=START,
    )


def catalog():
    return load_production_catalog(
        CONFIG_DIR / "simulator_production.yaml",
        DATA_DIR / "product_seed.csv",
        DATA_DIR / "line_seed.csv",
    )


def engine() -> ProductionExecutionEngine:
    config = yaml.safe_load(
        (CONFIG_DIR / "simulator_production.yaml").read_text(encoding="utf-8")
    )
    return ProductionExecutionEngine(
        catalog=catalog(),
        line_engine=LineExecutionEngine(config),
        event_factory=ProductionEventFactory(),
        deterministic_seed=20260921,
        configuration_version="1.0.0",
    )


def production_context() -> object:
    config = yaml.safe_load(
        (CONFIG_DIR / "simulator_context.yaml").read_text(encoding="utf-8")
    )
    return ProductionContextEngine(
        EnvironmentModel(config),
        ShiftResolver(config),
        WorkloadModel(config),
    ).build(
        "PLT-CHN-01",
        "CHN-L01",
        START,
        WorkloadInputs(120, 42, 1.0, 2.0, "RUNNING"),
        product_id="PROD-MOTOR-A01",
        product_cycle_time_seconds=42,
    )


def test_catalog_has_12_products_and_15_lines() -> None:
    c = catalog()
    assert len(c.products) == 12
    assert len(c.lines) == 15
    assert len(c.machines_by_line_type) == 15


def test_each_line_has_route_machines_for_every_product() -> None:
    c = catalog()
    for product_id in c.products:
        for line_id in c.lines:
            machines = c.route_machine_ids(line_id, product_id)
            assert len(machines) == len(c.product(product_id).route)
            assert len(set(machines)) == len(machines)


def test_order_and_batches_are_deterministic_and_reconcile() -> None:
    e = engine()
    run_context = context()
    order, events = e.create_order(
        run_context,
        "PLT-CHN-01",
        "CHN-L01",
        "PROD-MOTOR-A01",
        100,
        START,
        production_sequence=1,
    )
    batches = e.create_batches(run_context, order, 4)
    e.attach_batches(order, batches)
    assert order.production_order_id == UUID(
        "e13f3f52-1d1c-5d41-9cd0-bd1a9b1a6d07"
    )
    assert sum(batch.planned_quantity for batch in batches) == 100
    assert len({batch.batch_id for batch in batches}) == 4
    assert events[0].event_type == "ProductionOrderCreated"


def test_order_lifecycle_and_full_completion() -> None:
    e = engine()
    run_context = context()
    order, _ = e.create_order(
        run_context,
        "PLT-CHN-01",
        "CHN-L01",
        "PROD-HOUSING-E01",
        60,
        START,
        production_sequence=2,
    )
    batches = e.create_batches(run_context, order, 2)
    e.attach_batches(order, batches)

    assert e.release_order(run_context, order).event_type == "ProductionOrderReleased"
    assert e.start_order(run_context, order).event_type == "ProductionStarted"

    batch = batches[0]
    e.start_batch(run_context, order, batch)
    snapshot = LineCapacitySnapshot(
        line_id="CHN-L01",
        event_time=START,
        bottleneck_rate_units_min=60.0,
        nominal_bottleneck_rate_units_min=60.0,
        available=True,
        active_machine_ids=("CHN-L01-CNC01",),
        blocked_machine_ids=(),
        scenario_multiplier=1.0,
    )
    events = e.advance_batch(
        run_context,
        order,
        batch,
        snapshot,
        production_context(),
        elapsed_seconds=60,
        scenario_quality_multiplier=1.0,
    )

    assert batch.status is BatchStatus.COMPLETED
    assert batch.actual_quantity == 60
    assert batch.good_quantity + batch.rejected_quantity == batch.actual_quantity
    assert any(event.event_type == "BatchCompleted" for event in events)


def test_pause_and_resume_are_explicit_events() -> None:
    e = engine()
    run_context = context()
    order, _ = e.create_order(
        run_context,
        "PLT-CHN-01",
        "CHN-L01",
        "PROD-MOTOR-A01",
        40,
        START,
        production_sequence=3,
    )
    batches = e.create_batches(run_context, order, 1)
    e.attach_batches(order, batches)
    e.release_order(run_context, order)
    e.start_order(run_context, order)
    e.start_batch(run_context, order, batches[0])

    pause = e.pause_batch(run_context, order, batches[0], "MACHINE_FAULT")
    resume = e.resume_batch(run_context, order, batches[0], pause.event_id)

    assert pause.event_type == "ProductionPaused"
    assert resume.event_type == "ProductionResumed"
    assert batches[0].status is BatchStatus.IN_PROGRESS


def test_line_bottleneck_and_slowdown_loss() -> None:
    config = yaml.safe_load(
        (CONFIG_DIR / "simulator_production.yaml").read_text(encoding="utf-8")
    )
    line_engine = LineExecutionEngine(config)
    inputs = (
        MachineExecutionInput("CHN-L01-CNC01", "CNC", 120, True, 0.50, 1.0),
        MachineExecutionInput("CHN-L01-ROB01", "ROB", 80, True, 1.0, 1.0),
    )
    snapshot = line_engine.snapshot("CHN-L01", START, inputs)

    assert snapshot.nominal_bottleneck_rate_units_min == 80
    assert snapshot.bottleneck_rate_units_min == 60
    assert snapshot.available is True

    result = line_engine.advance_batch(
        catalog().product("PROD-MOTOR-A01") and __import__("industrial_sim.domain.production", fromlist=["ProductionBatch"]).ProductionBatch(
            batch_id=UUID("12345678-1234-5678-1234-567812345678"),
            production_order_id=RUN_ID,
            plant_id="PLT-CHN-01",
            line_id="CHN-L01",
            product_id="PROD-MOTOR-A01",
            planned_quantity=100,
            batch_sequence=1,
        ),
        snapshot,
        production_context(),
        60,
        0.99,
    )
    assert result.produced_quantity == 60
    assert result.loss_category == "SLOWDOWN"


def test_unavailable_line_produces_downtime_result() -> None:
    config = yaml.safe_load(
        (CONFIG_DIR / "simulator_production.yaml").read_text(encoding="utf-8")
    )
    line_engine = LineExecutionEngine(config)
    snapshot = line_engine.snapshot(
        "CHN-L01",
        START,
        (
            MachineExecutionInput("CHN-L01-CNC01", "CNC", 120, True),
            MachineExecutionInput("CHN-L01-ROB01", "ROB", 80, False),
        ),
    )
    assert snapshot.available is False
    assert snapshot.bottleneck_rate_units_min == 0.0
