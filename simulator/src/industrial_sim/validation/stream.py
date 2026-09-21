from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from industrial_sim.simulation.output import PartitionedEventStreamWriter
from industrial_sim.validation.models import ValidationResult
from industrial_sim.validation.quarantine import QuarantineWriter
from industrial_sim.validation.validator import SimulatorEventValidator


@dataclass(frozen=True)
class ValidationStreamStats:
    valid_count: int
    quarantined_count: int
    total_count: int


class ValidatedEventStreamWriter:
    """Apply the validation boundary before durable event-stream output."""

    def __init__(
        self,
        schema_root: str | Path,
        output_root: str | Path,
        ingestion_delay_min_ms: int = 20,
        ingestion_delay_max_ms: int = 1500,
    ) -> None:
        self.validator = SimulatorEventValidator(
            schema_root=schema_root,
            ingestion_delay_min_ms=ingestion_delay_min_ms,
            ingestion_delay_max_ms=ingestion_delay_max_ms,
        )
        self.valid_writer = PartitionedEventStreamWriter(output_root)
        self.quarantine_writer = QuarantineWriter(output_root)
        self.output_root = Path(output_root)

    def write(self, events: Iterable[object]) -> None:
        for event in events:
            result: ValidationResult = self.validator.validate_event(event)
            if result.valid:
                self.valid_writer.write((event,))
            else:
                self.quarantine_writer.write(event, result)

    def close(self) -> None:
        self.valid_writer.close()

    def stats(self) -> ValidationStreamStats:
        return ValidationStreamStats(
            valid_count=self.validator.state.valid_count,
            quarantined_count=self.validator.state.quarantined_count,
            total_count=(
                self.validator.state.valid_count
                + self.validator.state.quarantined_count
            ),
        )

    def manifest(self) -> dict:
        return {
            "validation": {
                "valid_count": self.validator.state.valid_count,
                "quarantined_count": self.validator.state.quarantined_count,
                "total_count": (
                    self.validator.state.valid_count
                    + self.validator.state.quarantined_count
                ),
            },
            "valid_event_stream": self.valid_writer.manifest(),
            "quarantine_count": self.quarantine_writer.count,
        }

    def write_manifest(self) -> Path:
        import json

        self.output_root.mkdir(parents=True, exist_ok=True)
        self.valid_writer.write_manifest()
        path = self.output_root / "validation_manifest.json"
        path.write_text(
            json.dumps(self.manifest(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return path
