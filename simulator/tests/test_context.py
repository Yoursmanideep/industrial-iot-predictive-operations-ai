from datetime import datetime, timezone
from pathlib import Path

import yaml

from industrial_sim.context.environment import EnvironmentModel
from industrial_sim.context.production_context import ProductionContextEngine
from industrial_sim.context.shift import ShiftResolver
from industrial_sim.context.workload import WorkloadInputs, WorkloadModel

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def load_context_config() -> dict:
    return yaml.safe_load((CONFIG_DIR / "simulator_context.yaml").read_text(encoding="utf-8"))


def test_shift_resolver_handles_all_three_shifts_and_midnight() -> None:
    resolver = ShiftResolver(load_context_config())
    assert resolver.resolve(datetime(2026, 9, 21, 6, 0, tzinfo=timezone.utc)).shift_id == "SH1"
    assert resolver.resolve(datetime(2026, 9, 21, 13, 59, tzinfo=timezone.utc)).shift_id == "SH2"
    assert resolver.resolve(datetime(2026, 9, 21, 16, 30, tzinfo=timezone.utc)).shift_id == "SH3"
    assert resolver.resolve(datetime(2026, 9, 21, 20, 30, tzinfo=timezone.utc)).shift_id == "SH1"


def test_environment_is_deterministic_for_same_inputs() -> None:
    model = EnvironmentModel(load_context_config())
    event_time = datetime(2026, 9, 21, 10, 0, tzinfo=timezone.utc)
    assert model.reading("PLT-CHN-01", event_time) == model.reading("PLT-CHN-01", event_time)


def test_plant_offset_changes_ambient_temperature() -> None:
    model = EnvironmentModel(load_context_config())
    event_time = datetime(2026, 9, 21, 10, 0, tzinfo=timezone.utc)
    chennai = model.reading("PLT-CHN-01", event_time)
    pune = model.reading("PLT-PUN-01", event_time)
    assert chennai.ambient_temperature_c != pune.ambient_temperature_c


def test_workload_responds_to_health_and_age() -> None:
    config = load_context_config()
    resolver = ShiftResolver(config)
    model = WorkloadModel(config)
    event_time = datetime(2026, 9, 21, 10, 0, tzinfo=timezone.utc)
    shift = resolver.resolve(event_time)
    healthy = model.evaluate(WorkloadInputs(120, 42, 1.0, 2.0, "RUNNING"), shift, event_time)
    degraded = model.evaluate(WorkloadInputs(120, 42, 0.50, 9.0, "RUNNING"), shift, event_time)
    assert degraded.workload_factor < healthy.workload_factor
    assert degraded.effective_capacity_units_min < healthy.effective_capacity_units_min


def test_non_running_state_suppresses_workload() -> None:
    config = load_context_config()
    resolver = ShiftResolver(config)
    model = WorkloadModel(config)
    event_time = datetime(2026, 9, 21, 10, 0, tzinfo=timezone.utc)
    result = model.evaluate(WorkloadInputs(120, 42, 1.0, 2.0, "FAULT"), resolver.resolve(event_time), event_time)
    assert result.workload_factor == 0.0


def test_product_cycle_time_affects_effective_capacity() -> None:
    config = load_context_config()
    resolver = ShiftResolver(config)
    model = WorkloadModel(config)
    event_time = datetime(2026, 9, 21, 10, 0, tzinfo=timezone.utc)
    shift = resolver.resolve(event_time)
    fast = model.evaluate(WorkloadInputs(120, 30, 1.0, 2.0, "RUNNING"), shift, event_time)
    slow = model.evaluate(WorkloadInputs(120, 60, 1.0, 2.0, "RUNNING"), shift, event_time)
    assert fast.effective_capacity_units_min > slow.effective_capacity_units_min


def test_production_context_combines_layers() -> None:
    config = load_context_config()
    engine = ProductionContextEngine(EnvironmentModel(config), ShiftResolver(config), WorkloadModel(config))
    event_time = datetime(2026, 9, 21, 10, 0, tzinfo=timezone.utc)
    context = engine.build("PLT-CHN-01", "CHN-L01", event_time, WorkloadInputs(120, 42, 1.0, 2.0, "RUNNING", 0.05), "PROD-MOTOR-A01", 42)
    assert context.plant_id == "PLT-CHN-01"
    assert context.line_id == "CHN-L01"
    assert context.shift_id in {"SH1", "SH2", "SH3"}
    assert context.workload.workload_factor > 0
