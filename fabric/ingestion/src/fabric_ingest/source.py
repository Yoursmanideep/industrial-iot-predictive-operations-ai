from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from fabric_ingest.identity import canonical_batch_key, ingestion_batch_id
from fabric_ingest.models import IngestionBatchManifest


class ValidatedSourceScanner:
    """Scan only validated event partitions emitted by the simulator."""

    def __init__(self, source_root: str | Path) -> None:
        self.source_root = Path(source_root)

    def discover(self) -> tuple[IngestionBatchManifest, ...]:
        manifests: list[IngestionBatchManifest] = []
        for path in sorted(self.source_root.glob("event_type=*/event_date=*/plant_id=*/*.jsonl")):
            manifests.append(self._manifest_for(path))
        return tuple(manifests)

    def _manifest_for(self, path: Path) -> IngestionBatchManifest:
        event_count = 0
        first_sequence: int | None = None
        last_sequence: int | None = None
        simulator_run_id: str | None = None
        schema_version: str | None = None
        event_type: str | None = None
        event_date: str | None = None
        plant_id: str | None = None
        digest = hashlib.sha256()

        for raw_line in path.read_bytes().splitlines(keepends=True):
            digest.update(raw_line)
            if not raw_line.strip():
                continue
            payload = json.loads(raw_line)
            event_count += 1
            current_run = payload.get("simulator_run_id")
            if simulator_run_id is None:
                simulator_run_id = current_run
            elif simulator_run_id != current_run:
                raise ValueError(f"Mixed simulator_run_id values in {path}")
            current_sequence = payload.get("generation_sequence")
            if current_sequence is not None:
                first_sequence = current_sequence if first_sequence is None else min(first_sequence, current_sequence)
                last_sequence = current_sequence if last_sequence is None else max(last_sequence, current_sequence)
            schema_version = schema_version or payload.get("schema_version")
            event_type = event_type or self._stream_name(payload.get("event_type"))
            plant_id = plant_id or payload.get("plant_id")

        parts = path.parts
        for part in parts:
            if part.startswith("event_date="):
                event_date = part.split("=", 1)[1]
            elif part.startswith("plant_id="):
                plant_id = plant_id or part.split("=", 1)[1]
            elif part.startswith("event_type="):
                event_type = event_type or part.split("=", 1)[1]

        if simulator_run_id is None or event_count == 0 or event_type is None or event_date is None or plant_id is None:
            raise ValueError(f"Incomplete validated source partition: {path}")

        source_hash = digest.hexdigest()
        key = canonical_batch_key(
            simulator_run_id,
            str(path.as_posix()),
            source_hash,
            first_sequence,
            last_sequence,
            event_count,
        )
        return IngestionBatchManifest(
            ingestion_batch_id=ingestion_batch_id(key),
            simulator_run_id=simulator_run_id,
            source_file_path=str(path),
            source_file_sha256=source_hash,
            event_type=event_type,
            event_date=event_date,
            plant_id=plant_id,
            event_count=event_count,
            first_generation_sequence=first_sequence,
            last_generation_sequence=last_sequence,
            created_at_utc=datetime.now(timezone.utc),
            schema_version=schema_version,
        )

    @staticmethod
    def _stream_name(event_type: str | None) -> str | None:
        if event_type == "MachineTelemetry":
            return "telemetry"
        if event_type in {
            "ProductionOrderCreated",
            "ProductionOrderReleased",
            "ProductionStarted",
            "BatchStarted",
            "UnitProduced",
            "BatchCompleted",
            "ProductionPaused",
            "ProductionResumed",
            "ProductionCompleted",
            "ProductionLossRecorded",
        }:
            return "production"
        if event_type:
            return "operational"
        return None