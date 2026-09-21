from __future__ import annotations

import uuid
from uuid import UUID


def run_namespace(simulator_run_id: UUID) -> UUID:
    """Derive the deterministic UUID namespace for a simulation run."""
    return uuid.uuid5(uuid.NAMESPACE_URL, f"industrial-iot/run/{simulator_run_id}")


def deterministic_event_id(
    simulator_run_id: UUID,
    entity_business_key: str,
    event_type: str,
    event_time: str,
    generation_sequence: int,
) -> UUID:
    """Create a reproducible event identity from the Stage 3.4 event key."""
    if generation_sequence < 1:
        raise ValueError("generation_sequence must start at 1.")

    key = "|".join(
        (
            str(entity_business_key),
            str(event_type),
            str(event_time),
            str(generation_sequence),
        )
    )
    return uuid.uuid5(run_namespace(simulator_run_id), key)
