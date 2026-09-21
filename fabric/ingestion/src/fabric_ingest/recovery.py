from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fabric_ingest.checkpoint import FileCheckpointStore
from fabric_ingest.identity import event_payload_hash


@dataclass(frozen=True)
class RecoveryResult:
    recovered: bool
    destination_path: str | None
    registered_event_count: int


class LocalIngestionRecovery:
    """Recover a committed raw landing from a source batch after process interruption."""

    def __init__(self, checkpoint_store: FileCheckpointStore) -> None:
        self.checkpoint_store = checkpoint_store

    def recover_registered_source(
        self,
        event_file: str | Path,
        event_ids: list[str],
    ) -> int:
        path = Path(event_file)
        payloads = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                payloads.append(__import__("json").loads(line))
        by_id = {payload["event_id"]: payload for payload in payloads}
        registered = 0
        for event_id in event_ids:
            payload = by_id.get(event_id)
            if payload is None:
                raise ValueError(f"Event {event_id} is missing from source file")
            result = self.checkpoint_store.register_event(event_id, payload)
            if result.status == "CONFLICT":
                raise ValueError(f"Conflicting payload for event {event_id}")
            if result.status == "NEW":
                registered += 1
        return registered