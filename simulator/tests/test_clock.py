from datetime import datetime, timezone

import pytest

from industrial_sim.engine.clock import SimulationClock


def test_clock_advances_by_tick() -> None:
    start = datetime(2026, 9, 21, 6, 0, tzinfo=timezone.utc)
    clock = SimulationClock(start, tick_seconds=5)
    assert clock.tick() == datetime(2026, 9, 21, 6, 0, 5, tzinfo=timezone.utc)


def test_clock_rejects_backwards_advance() -> None:
    start = datetime(2026, 9, 21, 6, 0, tzinfo=timezone.utc)
    clock = SimulationClock(start, tick_seconds=5)
    with pytest.raises(ValueError):
        clock.advance(-1)
