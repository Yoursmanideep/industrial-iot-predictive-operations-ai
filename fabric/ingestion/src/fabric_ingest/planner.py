from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from fabric_ingest.models import IngestionBatchManifest


@dataclass(frozen=True)
class FabricLoadPlan:
    ingestion_batch_id: str
    source_file_path: str
    one_lake_destination_path: str
    event_type: str
    event_date: str
    plant_id: str
    event_count: int
    first_generation_sequence: int | None
    last_generation_sequence: int | None

    def to_dict(self) -> dict:
        return self.__dict__.copy()


class FabricLoadPlanner:
    def __init__(self, bronze_root: str = "Files/bronze") -> None:
        self.bronze_root = bronze_root.rstrip("/")

    def build(self, manifest: IngestionBatchManifest) -> FabricLoadPlan:
        filename = Path(manifest.source_file_path).name
        destination = (
            f"{self.bronze_root}/event_type={manifest.event_type}/"
            f"event_date={manifest.event_date}/plant_id={manifest.plant_id}/{filename}"
        )
        return FabricLoadPlan(
            ingestion_batch_id=manifest.ingestion_batch_id,
            source_file_path=manifest.source_file_path,
            one_lake_destination_path=destination,
            event_type=manifest.event_type,
            event_date=manifest.event_date,
            plant_id=manifest.plant_id,
            event_count=manifest.event_count,
            first_generation_sequence=manifest.first_generation_sequence,
            last_generation_sequence=manifest.last_generation_sequence,
        )

    def write_plan_manifest(
        self,
        plans: list[FabricLoadPlan],
        destination: str | Path,
    ) -> Path:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {"plans": [plan.to_dict() for plan in plans]},
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return path