from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class IngestionBatchManifest:
    ingestion_batch_id: str
    simulator_run_id: str
    source_file_path: str
    source_file_sha256: str
    event_type: str
    event_date: str
    plant_id: str
    event_count: int
    first_generation_sequence: int | None
    last_generation_sequence: int | None
    created_at_utc: datetime
    schema_version: str | None = None
    destination_path: str | None = None

    def to_dict(self) -> dict:
        payload = self.__dict__.copy()
        payload["created_at_utc"] = self.created_at_utc.isoformat()
        return payload


@dataclass(frozen=True)
class IngestionCheckpoint:
    idempotency_key: str
    ingestion_batch_id: str
    simulator_run_id: str
    status: str
    accepted_event_count: int
    rejected_event_count: int = 0
    source_file_sha256: str | None = None
    updated_at_utc: datetime | None = None
    error_code: str | None = None

    def to_dict(self) -> dict:
        payload = self.__dict__.copy()
        if self.updated_at_utc is not None:
            payload["updated_at_utc"] = self.updated_at_utc.isoformat()
        return payload