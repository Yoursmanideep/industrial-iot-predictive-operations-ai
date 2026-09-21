from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from industrial_sim.production.events import ProductionEvent


@dataclass
class StreamStats:
    event_count: int = 0
    first_event_time: str | None = None
    last_event_time: str | None = None
    first_generation_sequence: int | None = None
    last_generation_sequence: int | None = None

    def observe(self, event) -> None:
        sequence = getattr(event, "generation_sequence", None)
        if sequence is None:
            raise ValueError("Every emitted simulator event requires generation_sequence")
        if self.last_generation_sequence is not None and sequence <= self.last_generation_sequence:
            raise ValueError(
                f"Generation sequence must increase strictly: "
                f"{sequence} <= {self.last_generation_sequence}"
            )
        self.last_generation_sequence = sequence
        if self.first_generation_sequence is None:
            self.first_generation_sequence = sequence

        event_time = event.event_time.isoformat()
        self.first_event_time = self.first_event_time or event_time
        self.last_event_time = event_time
        self.event_count += 1


class PartitionedEventStreamWriter:
    """Stream simulator events directly to event-type/date/plant JSONL partitions."""

    def __init__(self, output_root: str | Path) -> None:
        self.output_root = Path(output_root)
        self._handles: dict[Path, object] = {}
        self.stats: dict[str, StreamStats] = {}

    def write(self, events: Iterable[object]) -> None:
        for event in events:
            stream = self._stream_name(event)
            stats = self.stats.setdefault(stream, StreamStats())
            stats.observe(event)
            path = (
                self.output_root
                / f"event_type={stream}"
                / f"event_date={event.event_time.date().isoformat()}"
                / f"plant_id={event.plant_id}"
                / f"{stream.lower()}.jsonl"
            )
            path.parent.mkdir(parents=True, exist_ok=True)
            handle = self._handles.get(path)
            if handle is None:
                handle = path.open("w", encoding="utf-8")
                self._handles[path] = handle
            handle.write(
                json.dumps(
                    event.to_dict(),
                    separators=(",", ":"),
                    sort_keys=True,
                )
                + "\n"
            )

    def close(self) -> None:
        for handle in self._handles.values():
            handle.close()
        self._handles.clear()

    @staticmethod
    def _stream_name(event: object) -> str:
        if isinstance(event, ProductionEvent):
            return "production"
        event_type = getattr(event, "event_type", "")
        if event_type == "MachineTelemetry":
            return "telemetry"
        return "operational"

    def manifest(self) -> dict:
        return {
            "streams": {
                name: {
                    "event_count": stats.event_count,
                    "first_event_time": stats.first_event_time,
                    "last_event_time": stats.last_event_time,
                    "first_generation_sequence": stats.first_generation_sequence,
                    "last_generation_sequence": stats.last_generation_sequence,
                }
                for name, stats in sorted(self.stats.items())
            },
            "total_event_count": sum(stats.event_count for stats in self.stats.values()),
        }

    def write_manifest(self) -> Path:
        self.output_root.mkdir(parents=True, exist_ok=True)
        path = self.output_root / "run_event_manifest.json"
        path.write_text(
            json.dumps(self.manifest(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return path
