from datetime import datetime, timezone

from industrial_sim.config.loader import GenerationContract
from industrial_sim.domain.run import RunMode, RunStatus
from industrial_sim.engine.run_engine import RunEngine


def contract() -> GenerationContract:
    return GenerationContract(
        contract_version="1.0.0",
        default_seed=20260921,
        default_timezone="Asia/Kolkata",
        canonical_timestamp_timezone="UTC",
        raw={"time": {"live_tick_seconds": 5}},
    )


def test_create_run_uses_contract_defaults() -> None:
    start = datetime(2026, 9, 21, 6, 0, tzinfo=timezone.utc)
    end = datetime(2026, 9, 21, 6, 1, tzinfo=timezone.utc)
    run, context, clock = RunEngine(contract()).create_run(
        mode=RunMode.LIVE, start_time=start, end_time=end
    )
    assert run.status is RunStatus.RUNNING
    assert run.deterministic_seed == 20260921
    assert run.simulator_run_id == context.simulator_run_id
    assert context.generation_sequence == 0
    assert clock.tick_seconds == 5


def test_tick_updates_context() -> None:
    start = datetime(2026, 9, 21, 6, 0, tzinfo=timezone.utc)
    end = datetime(2026, 9, 21, 6, 0, 10, tzinfo=timezone.utc)
    _, context, clock = RunEngine(contract()).create_run(
        mode=RunMode.LIVE, start_time=start, end_time=end
    )
    assert RunEngine.tick(context, clock, end) is True
    assert context.current_time == datetime(
        2026, 9, 21, 6, 0, 5, tzinfo=timezone.utc
    )
