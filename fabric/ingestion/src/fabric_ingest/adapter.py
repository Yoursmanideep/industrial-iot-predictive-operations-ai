from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from fabric_ingest.checkpoint import FileCheckpointStore
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
    """Replay-safe Bronze landing adapter with an injectable Fabric transport boundary."""

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
        existing = self.checkpoint_store.get_batch(
            manifest.ingestion_batch_id.removeprefix("IBT-")
        )
        if existing and existing.get("status") == "COMPLETED" and existing.get("source_file_sha256") == manifest.source_file_sha256:
            return IngestionExecutionResult(
                ingestion_batch_id=manifest.ingestion_batch_id,
                status="SKIPPED_DUPLICATE",
                accepted_event_count=existing.get("accepted_event_count", 0),
                duplicate_event_count=manifest.event_count,
                conflict_event_count=0,
                destination_path=existing.get("destination_path"),
            )

        source_path = Path(manifest.source_file_path)
        if not source_path.is_file():
            failed = IngestionCheckpoint(
                idempotency_key=manifest.ingestion_batch_id.removeprefix("IBT-"),
                ingestion_batch_id=manifest.ingestion_batch_id,
                simulator_run_id=manifest.simulator_run_id,
                status="FAILED",
                accepted_event_count=0,
                rejected_event_count=manifest.event_count,
                source_file_sha256=manifest.source_file_sha256,
                updated_at_utc=datetime.now(timezone.utc),
                error_code="SOURCE_FILE_MISSING",
            )
            self.checkpoint_store.put_batch(failed)
            raise FileNotFoundError(source_path)

        destination = (
            self.bronze_root
            / f"event_type={manifest.event_type}"
            / f"event_date={manifest.event_date}"
            / f"plant_id={manifest.plant_id}"
            / source_path.name
        )
        destination.parent.mkdir(parents=True, exist_ok=True)

        self.checkpoint_store.put_batch(
            IngestionCheckpoint(
                idempotency_key=manifest.ingestion_batch_id.removeprefix("IBT-"),
                ingestion_batch_id=manifest.ingestion_batch_id,
                simulator_run_id=manifest.simulator_run_id,
                status="LOADING",
                accepted_event_count=0,
                source_file_sha256=manifest.source_file_sha256,
                updated_at_utc=datetime.now(timezone.utc),
            )
        )

        accepted = 0
        duplicates = 0
        conflicts = 0
        temp_destination = destination.with_suffix(destination.suffix + ".partial")
        with temp_destination.open("w", encoding="utf-8") as target:
            for line in source_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                event_id = payload["event_id"]
                registration = self.checkpoint_store.register_event(event_id, payload)
                if registration.status == "CONFLICT":
                    conflicts += 1
                    continue
                if registration.status == "DUPLICATE":
                    duplicates += 1
                    continue
                target.write(json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n")
                accepted += 1

        if conflicts:
            temp_destination.unlink(missing_ok=True)
            checkpoint = IngestionCheckpoint(
                idempotency_key=manifest.ingestion_batch_id.removeprefix("IBT-"),
                ingestion_batch_id=manifest.ingestion_batch_id,
                simulator_run_id=manifest.simulator_run_id,
                status="QUARANTINED",
                accepted_event_count=accepted,
                rejected_event_count=conflicts,
                source_file_sha256=manifest.source_file_sha256,
                updated_at_utc=datetime.now(timezone.utc),
                error_code="EVENT_ID_PAYLOAD_CONFLICT",
            )
            self.checkpoint_store.put_batch(checkpoint)
            return IngestionExecutionResult(
                ingestion_batch_id=manifest.ingestion_batch_id,
                status="QUARANTINED",
                accepted_event_count=accepted,
                duplicate_event_count=duplicates,
                conflict_event_count=conflicts,
                destination_path=None,
            )

        temp_destination.replace(destination)
        checkpoint = IngestionCheckpoint(
            idempotency_key=manifest.ingestion_batch_id.removeprefix("IBT-"),
            ingestion_batch_id=manifest.ingestion_batch_id,
            simulator_run_id=manifest.simulator_run_id,
            status="COMPLETED",
            accepted_event_count=accepted,
            rejected_event_count=0,
            source_file_sha256=manifest.source_file_sha256,
            updated_at_utc=datetime.now(timezone.utc),
        )
        self.checkpoint_store.put_batch(checkpoint)
        return IngestionExecutionResult(
            ingestion_batch_id=manifest.ingestion_batch_id,
            status="COMPLETED",
            accepted_event_count=accepted,
            duplicate_event_count=duplicates,
            conflict_event_count=conflicts,
            destination_path=str(destination),
        )