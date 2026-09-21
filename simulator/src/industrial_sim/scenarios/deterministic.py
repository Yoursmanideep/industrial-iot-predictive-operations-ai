from __future__ import annotations

import hashlib
from datetime import datetime
from uuid import UUID


def stable_fraction(*parts: object) -> float:
    raw = "|".join(str(part) for part in parts).encode("utf-8")
    integer = int.from_bytes(hashlib.sha256(raw).digest()[:8], "big")
    return integer / float(2**64 - 1)


def choose_duration_minutes(
    simulator_run_id: UUID,
    machine_id: str,
    scenario_id: str,
    started_at: datetime,
    minimum_minutes: int,
    maximum_minutes: int,
) -> int:
    if maximum_minutes < minimum_minutes:
        raise ValueError("maximum_minutes cannot be below minimum_minutes")
    if maximum_minutes == minimum_minutes:
        return minimum_minutes

    fraction = stable_fraction(
        "scenario-duration",
        simulator_run_id,
        machine_id,
        scenario_id,
        started_at.isoformat(),
    )
    span = maximum_minutes - minimum_minutes
    return minimum_minutes + int(fraction * (span + 1))
