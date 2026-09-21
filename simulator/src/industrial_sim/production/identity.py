from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from industrial_sim.lineage.identity import run_namespace


def deterministic_production_order_id(
    simulator_run_id: UUID,
    plant_id: str,
    line_id: str,
    planned_start_time: datetime,
    production_sequence: int,
) -> UUID:
    key = "|".join((
        "production-order", plant_id, line_id,
        planned_start_time.isoformat(), str(production_sequence),
    ))
    return uuid.uuid5(run_namespace(simulator_run_id), key)


def deterministic_batch_id(
    simulator_run_id: UUID,
    production_order_id: UUID,
    batch_sequence: int,
) -> UUID:
    key = "|".join(("batch", str(production_order_id), str(batch_sequence)))
    return uuid.uuid5(run_namespace(simulator_run_id), key)


def deterministic_operation_id(
    simulator_run_id: UUID,
    production_order_id: UUID,
    batch_sequence: int,
    route_sequence: int,
) -> UUID:
    key = "|".join((
        "operation", str(production_order_id),
        str(batch_sequence), str(route_sequence),
    ))
    return uuid.uuid5(run_namespace(simulator_run_id), key)