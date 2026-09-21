from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from industrial_sim.production.events import ProductionEvent


@dataclass(frozen=True)
class EventBatchManifest:
    event_count: int
    partition_count: int
    first_event_time: str | None
    last_event_time: str | None
    files: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "event_count": self.event_count,
            "partition_count": self.partition_count,
            "first_event_time": self.first_event_time,
            "last_event_time": self.last_event_time,
            "files": list(self.files),
        }


class PartitionedProductionEventWriter:
    """Write canonical production events as deterministic JSONL partitions."""

    def __init__(self, output_root: str | Path) -> None:
        self.output_root = Path(output_root)

    def write(self, events: Iterable[ProductionEvent]) -> EventBatchManifest:
        ordered = sorted(
            events,
            key=lambda event: (
                event.event_time,
                event.generation_sequence or 0,
                event.event_id,
            ),
        )
        handles: dict[Path, object] = {}
        files: list[Path] = []
        count = 0
        try:
            for event in ordered:
                event_date = event.event_time.date().isoformat()
                path = (
                    self.output_root
                    / f"event_date={event_date}"
                    / f"plant_id={event.plant_id}"
                    / "production_events.jsonl"
                )
                path.parent.mkdir(parents=True, exist_ok=True)
                if path not in handles:
                    handles[path] = path.open("w", encoding="utf-8")
                    files.append(path)
                handles[path].write(
                    json.dumps(
                        event.to_dict(),
                        separators=(",", ":"),
                        sort_keys=True,
                    )
                    + "\n"
                )
                count += 1
        finally:
            for handle in handles.values():
                handle.close()

        first_event_time = ordered[0].event_time.isoformat() if ordered else None
        last_event_time = ordered[-1].event_time.isoformat() if ordered else None
        manifest = EventBatchManifest(
            event_count=count,
            partition_count=len(files),
            first_event_time=first_event_time,
            last_event_time=last_event_time,
            files=tuple(str(path) for path in files),
        )
        manifest_path = self.output_root / "production_event_manifest.json"
        self.output_root.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return manifest
