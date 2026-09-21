from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class ValidationError:
    code: str
    message: str
    field: str | None = None

    def to_dict(self) -> dict[str, str]:
        payload = {
            "code": self.code,
            "message": self.message,
        }
        if self.field is not None:
            payload["field"] = self.field
        return payload


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: tuple[ValidationError, ...] = ()

    @classmethod
    def ok(cls) -> "ValidationResult":
        return cls(valid=True)

    @classmethod
    def invalid(cls, errors: list[ValidationError]) -> "ValidationResult":
        return cls(valid=False, errors=tuple(errors))


@dataclass
class ValidationRunState:
    simulator_run_id: str | None = None
    last_seen_generation_sequence: int = 0
    last_seen_generation_sequence: int = 0
    last_generation_sequence: int = 0
    last_event_time: datetime | None = None
    event_ids: set[str] = field(default_factory=set)
    event_index: dict[str, dict] = field(default_factory=dict)
    event_correlations: dict[str, str | None] = field(default_factory=dict)
    quarantined_count: int = 0
    valid_count: int = 0

    def reset(self) -> None:
        self.simulator_run_id = None
        self.last_seen_generation_sequence = 0
        self.last_seen_generation_sequence = 0
        self.last_generation_sequence = 0
        self.last_event_time = None
        self.event_ids.clear()
        self.event_index.clear()
        self.event_correlations.clear()
        self.quarantined_count = 0
        self.valid_count = 0
