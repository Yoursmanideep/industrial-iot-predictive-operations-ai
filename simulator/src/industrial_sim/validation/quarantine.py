from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from industrial_sim.validation.models import ValidationResult


class QuarantineWriter:
    """Preserve invalid event payloads and validation diagnostics without rewriting them."""

    def __init__(self, output_root: str | Path) -> None:
        self.output_root = Path(output_root)
        self.count = 0

    def write(self, event: object, result: ValidationResult) -> Path:
        if result.valid:
            raise ValueError("QuarantineWriter accepts invalid validation results only")

        payload = event.to_dict()
        event_time = payload.get("event_time")
        if event_time:
            day = event_time[:10]
        else:
            day = "unknown"

        record = {
            "quarantine_id": f"QRT-{uuid4()}",
            "quarantined_at_utc": datetime.now(timezone.utc).isoformat(),
            "reason_codes": [error.code for error in result.errors],
            "validation_errors": [error.to_dict() for error in result.errors],
            "event_id": payload.get("event_id"),
            "event_type": payload.get("event_type"),
            "simulator_run_id": payload.get("simulator_run_id"),
            "original_payload": payload,
        }

        path = (
            self.output_root
            / "quarantine"
            / f"event_date={day}"
            / f"event_type={payload.get('event_type', 'UNKNOWN')}"
            / "quarantine.jsonl"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    record,
                    separators=(",", ":"),
                    sort_keys=True,
                )
                + "\n"
            )

        self.count += 1
        return path
