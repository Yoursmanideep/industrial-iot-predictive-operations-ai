from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from industrial_sim.engine.context import SimulationContext
from industrial_sim.production.catalog import load_production_catalog
from industrial_sim.production.engine import ProductionExecutionEngine
from industrial_sim.production.events import ProductionEventFactory
from industrial_sim.production.line_engine import LineExecutionEngine
import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data_reference" / "seed"
RUN_ID = UUID("12345678-1234-5678-1234-567812345678")
START = datetime(2026, 9, 21, 6, 0, tzinfo=timezone.utc)


def test_event_factory_serializes_canonical_identifiers() -> None:
    catalog = load_production_catalog(CONFIG_DIR / "simulator_production.yaml", DATA_DIR / "product_seed.csv", DATA_DIR / "line_seed.csv")
    config = yaml.safe_load((CONFIG_DIR / "simulator_production.yaml").read_text(encoding="utf-8"))
    engine = ProductionExecutionEngine(
        catalog=catalog,
        line_engine=LineExecutionEngine(config),
        event_factory=ProductionEventFactory(),
        deterministic_seed=20260921,
        configuration_version="1.0.0",
    )
    context = SimulationContext(
        simulator_run_id=RUN_ID,
        deterministic_seed=20260921,
        generator_version="0.1.0",
        configuration_version="1.0.0",
        current_time=START,
    )
    order, events = engine.create_order(
        context,
        "PLT-CHN-01",
        "CHN-L01",
        "PROD-MOTOR-A01",
        100,
        START,
        1,
    )
    payload = events[0].to_dict()
    assert payload["event_id"].startswith("EVT-")
    assert payload["production_order_id"].startswith("PO-")
    assert payload["product_id"] == "PROD-MOTOR-A01"
    assert payload["planned_quantity"] == 100
    assert payload["quantity_uom"] == "unit"
    assert payload["simulator_run_id"].startswith("RUN-")
    assert payload["generation_sequence"] == 1
