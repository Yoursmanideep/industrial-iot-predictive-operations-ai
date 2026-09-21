from __future__ import annotations

import hashlib


def canonical_batch_key(
    simulator_run_id: str,
    logical_source_key: str,
    source_file_sha256: str,
    first_generation_sequence: int | None,
    last_generation_sequence: int | None,
    event_count: int,
) -> str:
    raw = "|".join(
        (
            simulator_run_id,
            logical_source_key,
            source_file_sha256,
            str(first_generation_sequence or ""),
            str(last_generation_sequence or ""),
            str(event_count),
        )
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def ingestion_batch_id(idempotency_key: str) -> str:
    if len(idempotency_key) != 64:
        raise ValueError("idempotency_key must be a SHA-256 hex digest")
    return f"IBT-{idempotency_key}"


def event_payload_hash(payload: dict) -> str:
    import json

    canonical = json.dumps(
        payload,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()