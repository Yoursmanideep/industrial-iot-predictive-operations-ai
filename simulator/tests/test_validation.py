from datetime import datetime, timezone, timedelta
from pathlib import Path
from uuid import UUID

from industrial_sim.domain.production import ProductionOrder
from industrial_sim.production.events import ProductionEventFactory
from industrial_sim.validation.quarantine import QuarantineWriter
from industrial_sim.validation.validator import SimulatorEventValidator

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_ROOT = ROOT / "schemas"
RUN_ID = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
START = datetime(2026, 9, 21, 6, 0, tzinfo=timezone.utc)


def make_order() -> ProductionOrder:
    return ProductionOrder(
        production_order_id=UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),
        plant_id="PLT-CHN-01",
        line_id="CHN-L01",
        product_id="PROD-MOTOR-A01",
        planned_quantity=100,
        quantity_uom="unit",
        planned_start_time=START,
        planned_end_time=START + timedelta(hours=1),
    )


def make_event(
    event_type: str,
    sequence: int,
    **kwargs,
):
    return ProductionEventFactory().build(
        run_id=RUN_ID,
        production_order=make_order(),
        event_type=event_type,
        event_time=START + timedelta(seconds=sequence),
        generation_sequence=sequence,
        deterministic_seed=20260921,
        configuration_version="1.0.0",
        **kwargs,
    )


def test_valid_production_event_is_accepted() -> None:
    validator = SimulatorEventValidator(SCHEMA_ROOT)
    result = validator.validate_event(
        make_event(
            "ProductionOrderCreated",
            1,
            product_id="PROD-MOTOR-A01",
            planned_quantity=100,
            quantity_uom="unit",
            planned_start_time=START,
            planned_end_time=START + timedelta(hours=1),
        )
    )
    assert result.valid
    assert validator.state.valid_count == 1
    assert validator.state.quarantined_count == 0


def test_invalid_schema_event_is_quarantined_without_sequence_cascade() -> None:
    validator = SimulatorEventValidator(SCHEMA_ROOT)
    first = make_event(
        "ProductionOrderCreated",
        1,
        product_id="PROD-MOTOR-A01",
        planned_quantity=100,
        quantity_uom="unit",
        planned_start_time=START,
        planned_end_time=START + timedelta(hours=1),
    )
    assert validator.validate_event(first).valid

    invalid = make_event(
        "ProductionOrderCreated",
        2,
        product_id="PROD-MOTOR-A01",
        planned_quantity=100,
        quantity_uom="not-a-unit",
        planned_start_time=START,
        planned_end_time=START + timedelta(hours=1),
    )
    assert not validator.validate_event(invalid).valid
    assert validator.state.quarantined_count == 1

    valid_after_quarantine = make_event(
        "ProductionOrderReleased",
        3,
        product_id="PROD-MOTOR-A01",
        planned_quantity=100,
        quantity_uom="unit",
    )
    assert validator.validate_event(valid_after_quarantine).valid
    assert validator.state.valid_count == 2


def test_missing_causation_parent_is_rejected() -> None:
    validator = SimulatorEventValidator(SCHEMA_ROOT)
    event = make_event(
        "ProductionOrderReleased",
        1,
        product_id="PROD-MOTOR-A01",
        planned_quantity=100,
        quantity_uom="unit",
        causation_id="EVT-11111111-1111-1111-1111-111111111111",
    )
    result = validator.validate_event(event)
    assert not result.valid
    assert any(error.code == "CAUSATION_PARENT_MISSING" for error in result.errors)


def test_production_quantity_invariant_is_rejected() -> None:
    validator = SimulatorEventValidator(SCHEMA_ROOT)
    event = make_event(
        "UnitProduced",
        1,
        batch_id="BAT-11111111-1111-1111-1111-111111111111",
        product_id="PROD-MOTOR-A01",
        actual_quantity=10,
        good_quantity=8,
        rejected_quantity=5,
        quantity_uom="unit",
    )
    result = validator.validate_event(event)
    assert not result.valid
    assert any(
        error.code == "PRODUCTION_QUANTITY_INVARIANT"
        for error in result.errors
    )


def test_quarantine_metadata_is_deterministic(tmp_path: Path) -> None:
    writer = QuarantineWriter(tmp_path)
    validator = SimulatorEventValidator(SCHEMA_ROOT)
    event = make_event(
        "ProductionOrderReleased",
        1,
        product_id="PROD-MOTOR-A01",
        planned_quantity=100,
        quantity_uom="bad-uom",
    )
    result = validator.validate_event(event)
    assert not result.valid

    first_path = writer.write(event, result)
    second_path = writer.write(event, result)
    assert first_path == second_path

    lines = first_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert '"quarantine_id":"QRT-' in lines[0]
    assert '"original_payload":' in lines[0]
