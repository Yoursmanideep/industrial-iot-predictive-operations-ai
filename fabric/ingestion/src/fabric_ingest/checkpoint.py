from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path

from fabric_ingest.identity import event_payload_hash
from fabric_ingest.models import IngestionCheckpoint


@dataclass(frozen=True)
class EventRegistrationResult:
    status: str
    event_id: str
    payload_hash: str
    existing_payload_hash: str | None = None


class FileCheckpointStore:
    """Development/test checkpoint store mirroring the Fabric control-table semantics."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._document = self._load()

    def _load(self) -> dict:
        if not self.path.is_file():
            return {"batches": {}, "events": {}}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._document, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def get_batch(self, idempotency_key: str) -> dict | None:
        return self._document["batches"].get(idempotency_key)

    def put_batch(self, checkpoint: IngestionCheckpoint) -> None:
        self._document["batches"][checkpoint.idempotency_key] = checkpoint.to_dict()
        self._save()

    def register_event(self, event_id: str, payload: dict) -> EventRegistrationResult:
        payload_hash = event_payload_hash(payload)
        existing = self._document["events"].get(event_id)
        if existing is None:
            self._document["events"][event_id] = payload_hash
            self._save()
            return EventRegistrationResult(
                status="NEW",
                event_id=event_id,
                payload_hash=payload_hash,
            )
        if existing == payload_hash:
            return EventRegistrationResult(
                status="DUPLICATE",
                event_id=event_id,
                payload_hash=payload_hash,
                existing_payload_hash=existing,
            )
        return EventRegistrationResult(
            status="CONFLICT",
            event_id=event_id,
            payload_hash=payload_hash,
            existing_payload_hash=existing,
        )

    def snapshot(self) -> dict:
        return self._document.copy()