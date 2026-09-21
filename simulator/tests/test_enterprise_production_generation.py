from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from industrial_sim.production.batch_writer import PartitionedProductionEventWriter
from industrial_sim.production.enterprise_run import generate_production_plan
from industrial_sim.production.generator import EnterpriseProductionGenerator
from industrial_sim.production.catalog import load_production_catalog
from industrial_sim.production.engine import ProductionExecutionEngine
import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data_reference" / "seed"
RUN_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
START = datetime(2026, 9, 21, 0, 0, tzinfo=timezone.utc)


def make_generator() -> EnterpriseProductionGenerator:
    catalog = load_production_catalog(
        CONFIG_DIR / "simulator_production.yaml",
        DATA_DIR / "product_seed.csv",
        DATA_DIR / "line_seed.csv",
    )
    execution = ProductionExecutionEngine.from_config(
        catalog,
        CONFIG_DIR / "simulator_production.yaml",
        deterministic_seed=20260921,
        configuration_version="1.0.0",
    )
    generation_config = yaml.safe_load(
        (CONFIG_DIR / "simulator_data_generation.yaml").read_text(encoding="utf-8")
    )
    return EnterpriseProductionGenerator(
        catalog=catalog,
        execution_engine=execution,
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


def test_one_day_generates_enterprise_order_volume_and_keeps_orders_in_plant() -> None:
    generator = make_generator()
    from industrial_sim.engine.context import SimulationContext

    context = SimulationContext(
        simulator_run_id=RUN_ID,
        deterministic_seed=20260921,
        generator_version="0.1.0",
        configuration_version="1.0.0",
        current_time=START,
    )
    plans = generator.generate_day(
        context,
        START,
        ("PLT-CHN-01", "PLT-PUN-01", "PLT-CBE-01"),
    )

    assert 90 <= len(plans) <= 180
    assert {plan.plant_id for plan in plans} == {
        "PLT-CHN-01",
        "PLT-PUN-01",
        "PLT-CBE-01",
    }
    for plan in plans:
        assert plan.line_id.startswith(plan.plant_id[4:7] + "-")
        assert 100 <= plan.planned_quantity <= 2500
        assert 1 <= plan.batch_count <= 8


def test_same_seed_produces_same_first_day_plan() -> None:
    generator = make_generator()
    from industrial_sim.engine.context import SimulationContext

    kwargs = dict(
        simulator_run_id=RUN_ID,
        deterministic_seed=20260921,
        generator_version="0.1.0",
        configuration_version="1.0.0",
        current_time=START,
    )
    plans_a = generator.generate_day(
        SimulationContext(**kwargs),
        START,
        ("PLT-CHN-01", "PLT-PUN-01", "PLT-CBE-01"),
    )
    plans_b = generator.generate_day(
        SimulationContext(**kwargs),
        START,
        ("PLT-CHN-01", "PLT-PUN-01", "PLT-CBE-01"),
    )

    assert plans_a == plans_b


def test_partitioned_writer_orders_and_partitions_events(tmp_path: Path) -> None:
    from industrial_sim.production.events import ProductionEvent

    event_a = ProductionEvent(
        event_id="EVT-aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        event_type="ProductionOrderCreated",
        schema_version="1.0.0",
        event_time=datetime(2026, 9, 21, 7, 0, tzinfo=timezone.utc),
        ingestion_time=datetime(2026, 9, 21, 7, 0, 0, 100000, tzinfo=timezone.utc),
        source_system="simulator",
        plant_id="PLT-CHN-01",
        production_order_id="PO-aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        generation_sequence=2,
    )
    event_b = ProductionEvent(
        event_id="EVT-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        event_type="ProductionOrderReleased",
        schema_version="1.0.0",
        event_time=datetime(2026, 9, 21, 6, 0, tzinfo=timezone.utc),
        ingestion_time=datetime(2026, 9, 21, 6, 0, 0, 100000, tzinfo=timezone.utc),
        source_system="simulator",
        plant_id="PLT-PUN-01",
        production_order_id="PO-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        generation_sequence=3,
    )

    manifest = PartitionedProductionEventWriter(tmp_path).write([event_a, event_b])

    assert manifest.event_count == 2
    assert manifest.partition_count == 2
    assert manifest.first_event_time == event_b.event_time.isoformat()
    assert manifest.last_event_time == event_a.event_time.isoformat()
    assert all(Path(file).is_file() for file in manifest.files)
