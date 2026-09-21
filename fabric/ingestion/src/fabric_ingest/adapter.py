from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from fabric_ingest.checkpoint import FileCheckpointStore
from fabric_ingest.identity import event_payload_hash
from fabric_ingest.models import IngestionBatchManifest, IngestionCheckpoint
from fabric_ingest.source import ValidatedSourceScanner


@dataclass(frozen=True)
class IngestionExecutionResult:
    ingestion_batch_id: str
    status: str
    accepted_event_count: int
    duplicate_event_count: int
    conflict_event_count: int
    destination_path: str | None


class FabricIngestionAdapter:
    """Replay-safe Bronze landing adapter with a pluggable Fabric transport boundary."""

    def __init__(
        self,
        checkpoint_store: FileCheckpointStore,
        bronze_root: str | Path,
    ) -> None:
        self.checkpoint_store = checkpoint_store
        self.bronze_root = Path(bronze_root)

    def plan(self, source_root: str | Path) -> tuple[IngestionBatchManifest, ...]:
        return ValidatedSourceScanner(source_root).discover()

    def ingest(self, manifest: IngestionBatchManifest) -> IngestionExecutionResult:
        idempotency_key = manifest.ingestion_batch_id.removeprefix("IBT-")
        existing = self.checkpoint_store.get_batch(idempotency_key)
        destination = self._destination_for(manifest)

        if existing and existing.get("status") == "COMPLETED":
            if existing.get("source_file_sha256") == manifest.source_file_sha256:
                return IngestionExecutionResult(
                    ingestion_batch_id=manifest.ingestion_batch_id,
                    status="SKIPPED_DUPLICATE",
                    accepted_event_count=int(existing.get("accepted_event_count", 0)),
                    duplicate_event_count=manifest.event_count,
                    conflict_event_count=0,
                    destination_path=existing.get("destination_path") or str(destination),
                )
            return IngestionExecutionResult(
                ingestion_batch_id=manifest.ingestion_batch_id,
                status="QUARANTINED",
                accepted_event_count=0,
                duplicate_event_count=0,
                conflict_event_count=manifest.event_count,
                destination_path=None,
            )

        source_path = Path(manifest.source_file_path)
        if not source_path.is_file():
            self.checkpoint_store.put_batch(
                IngestionCheckpoint(
                    idempotency_key=idempotency_key,
                    ingestion_batch_id=manifest.ingestion_batch_id,
                    simulator_run_id=manifest.simulator_run_id,
                    status="FAILED",
                    accepted_event_count=0,
                    rejected_event_count=manifest.event_count,
                    source_file_sha256=manifest.source_file_sha256,
                    updated_at_utc=datetime.now(timezone.utc),
                    error_code="SOURCE_FILE_MISSING",
                )
            )
            raise FileNotFoundError(source_path)

        destination.parent.mkdir(parents=True, exist_ok=True)
        self.checkpoint_store.put_batch(
            IngestionCheckpoint(
                idempotency_key=idempotency_key,
                ingestion_batch_id=manifest.ingestion_batch_id,
                simulator_run_id=manifest.simulator_run_id,
                status="LOADING",
                accepted_event_count=0,
                rejected_event_count=0,
                source_file_sha256=manifest.source_file_sha256,
                updated_at_utc=datetime.now(timezone.utc),
            )
        )

        pending: list[tuple[dict, str]] = []
        duplicates = 0
        conflicts = 0
        for line in source_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            event_id = payload["event_id"]
            existing_hash = self.checkpoint_store.snapshot()["events"].get(event_id)
            payload_hash = event_payload_hash(payload)
            if existing_hash is None:
                pending.append((payload, payload_hash))
            elif existing_hash == payload_hash:
                duplicates += 1
            else:
                conflicts += 1

        if conflicts:
            self.checkpoint_store.put_batch(
                IngestionCheckpoint(
                    idempotency_key=idempotency_key,
                    ingestion_batch_id=manifest.ingestion_batch_id,
                    simulator_run_id=manifest.simulator_run_id,
                    status="QUARANTINED",
                    accepted_event_count=0,
                    rejected_event_count=conflicts,
                    source_file_sha256=manifest.source_file_sha256,
                    updated_at_utc=datetime.now(timezone.utc),
                    error_code="EVENT_ID_PAYLOAD_CONFLICT",
                )
            )
            return IngestionExecutionResult(
                ingestion_batch_id=manifest.ingestion_batch_id,
                status="QUARANTINED",
                accepted_event_count=0,
                duplicate_event_count=duplicates,
                conflict_event_count=conflicts,
                destination_path=None,
            )

        temp_destination = destination.with_suffix(destination.suffix + ".partial")
        with temp_destination.open("w", encoding="utf-8") as target:
            for payload, _ in pending:
                target.write(
                    json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n"
                )

        if destination.exists():
            destination.unlink()
        temp_destination.replace(destination)

        for payload, _ in pending:
            self.checkpoint_store.register_event(payload["event_id"], payload)

        checkpoint = IngestionCheckpoint(
            idempotency_key=idempotency_key,
            ingestion_batch_id=manifest.ingestion_batch_id,
            simulator_run_id=manifest.simulator_run_id,
            status="COMPLETED",
            accepted_event_count=len(pending),
            rejected_event_count=0,
            source_file_sha256=manifest.source_file_sha256,
            updated_at_utc=datetime.now(timezone.utc),
        )
        checkpoint_dict = checkpoint.to_dict()
        checkpoint_dict["destination_path"] = str(destination)
        self.checkpoint_store._document["batches"][idempotency_key] = checkpoint_dict
        self.checkpoint_store._save()

        return IngestionExecutionResult(
            ingestion_batch_id=manifest.ingestion_batch_id,
            status="COMPLETED",
            accepted_event_count=len(pending),
            duplicate_event_count=duplicates,
            conflict_event_count=conflicts,
            destination_path=str(destination),
        )

    def _destination_for(self, manifest: IngestionBatchManifest) -> Path:
        return (
            self.bronze_root
            / f"event_type={manifest.event_type}"
            / f"event_date={manifest.event_date}"
            / f"plant_id={manifest.plant_id}"
            / Path(manifest.source_file_path).name
        )