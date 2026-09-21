from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from industrial_sim.domain.run import RunMode
from industrial_sim.validation.models import ValidationError, ValidationResult, ValidationRunState


class SimulatorEventValidator:
    """Validate generated simulator events against schemas and run-level invariants."""

    def __init__(
        self,
        schema_root: str | Path,
        ingestion_delay_min_ms: int = 20,
        ingestion_delay_max_ms: int = 1500,
    ) -> None:
        self.schema_root = Path(schema_root)
        self.ingestion_delay_min_ms = ingestion_delay_min_ms
        self.ingestion_delay_max_ms = ingestion_delay_max_ms
        self.state = ValidationRunState()
        self._validators = self._load_validators()

    def reset(self) -> None:
        self.state.reset()

    def validate_event(self, event: object) -> ValidationResult:
        payload = event.to_dict()
        errors: list[ValidationError] = []

        schema_validator = self._schema_validator(payload)
        if schema_validator is None:
            errors.append(
                ValidationError(
                    "SCHEMA_NOT_FOUND",
                    f"No governed schema found for event_type={payload.get('event_type')}",
                    "event_type",
                )
            )
        else:
            for error in sorted(
                schema_validator.iter_errors(payload),
                key=lambda item: (list(item.path), item.message),
            ):
                field = ".".join(str(part) for part in error.path) or None
                errors.append(
                    ValidationError(
                        "SCHEMA_VALIDATION_ERROR",
                        error.message,
                        field,
                    )
                )

        errors.extend(self._validate_lineage(payload))
        errors.extend(self._validate_temporal(payload))
        errors.extend(self._validate_causation(payload))
        errors.extend(self._validate_correlation(payload))
        errors.extend(self._validate_scenario_lineage(payload))
        errors.extend(self._validate_business_rules(payload))

        result = ValidationResult.ok() if not errors else ValidationResult.invalid(errors)
        self._advance_observed_cursor(payload)
        if result.valid:
            self._accept(payload)
        else:
            self.state.quarantined_count += 1
        return result

    def _load_validators(self) -> dict[str, Draft202012Validator]:
        mapping = {
            "MachineTelemetry": self.schema_root / "telemetry" / "machine_telemetry.schema.json",
            "Production": self.schema_root / "events" / "production_event.schema.json",
            "Operational": self.schema_root / "events" / "machine_operational_event.schema.json",
        }
        validators: dict[str, Draft202012Validator] = {}
        for name, path in mapping.items():
            schema = json.loads(path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
            validators[name] = Draft202012Validator(
                schema,
                format_checker=FormatChecker(),
            )
        return validators

    def _schema_validator(self, payload: dict[str, Any]) -> Draft202012Validator | None:
        event_type = payload.get("event_type")
        if event_type == "MachineTelemetry":
            return self._validators["MachineTelemetry"]
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
            return self._validators["Production"]
        if event_type:
            return self._validators["Operational"]
        return None

    def _validate_lineage(self, payload: dict[str, Any]) -> list[ValidationError]:
        errors: list[ValidationError] = []
        run_id = payload.get("simulator_run_id")
        sequence = payload.get("generation_sequence")
        event_id = payload.get("event_id")

        if run_id is None:
            errors.append(ValidationError("MISSING_RUN_LINEAGE", "simulator_run_id is required", "simulator_run_id"))
        elif self.state.simulator_run_id is None:
            self.state.simulator_run_id = run_id
        elif run_id != self.state.simulator_run_id:
            errors.append(
                ValidationError(
                    "MULTIPLE_RUN_IDS",
                    f"Event belongs to {run_id}, expected {self.state.simulator_run_id}",
                    "simulator_run_id",
                )
            )

        if not isinstance(sequence, int) or isinstance(sequence, bool):
            errors.append(
                ValidationError(
                    "INVALID_GENERATION_SEQUENCE",
                    "generation_sequence must be an integer",
                    "generation_sequence",
                )
            )
        elif sequence != self.state.last_seen_generation_sequence + 1:
            errors.append(
                ValidationError(
                    "GENERATION_SEQUENCE_GAP",
                    f"Expected generation_sequence={self.state.last_seen_generation_sequence + 1}, received {sequence}",
                    "generation_sequence",
                )
            )

        if not event_id:
            errors.append(ValidationError("MISSING_EVENT_ID", "event_id is required", "event_id"))
        elif event_id in self.state.event_ids:
            errors.append(
                ValidationError(
                    "DUPLICATE_EVENT_ID",
                    f"event_id {event_id} has already been accepted",
                    "event_id",
                )
            )

        return errors

    def _validate_temporal(self, payload: dict[str, Any]) -> list[ValidationError]:
        errors: list[ValidationError] = []
        try:
            event_time = datetime.fromisoformat(payload["event_time"].replace("Z", "+00:00"))
            ingestion_time = datetime.fromisoformat(payload["ingestion_time"].replace("Z", "+00:00"))
        except (KeyError, TypeError, ValueError):
            return errors

        if ingestion_time < event_time:
            errors.append(
                ValidationError(
                    "INGESTION_BEFORE_EVENT",
                    "ingestion_time cannot precede event_time",
                    "ingestion_time",
                )
            )
        if event_time.utcoffset() is None or event_time.utcoffset().total_seconds() != 0:
            errors.append(
                ValidationError(
                    "EVENT_TIME_NOT_UTC",
                    "event_time must use UTC offset +00:00",
                    "event_time",
                )
            )
        if ingestion_time.utcoffset() is None or ingestion_time.utcoffset().total_seconds() != 0:
            errors.append(
                ValidationError(
                    "INGESTION_TIME_NOT_UTC",
                    "ingestion_time must use UTC offset +00:00",
                    "ingestion_time",
                )
            )

        delay_ms = (ingestion_time - event_time).total_seconds() * 1000
        if delay_ms < self.ingestion_delay_min_ms or delay_ms > self.ingestion_delay_max_ms:
            errors.append(
                ValidationError(
                    "INGESTION_DELAY_OUT_OF_BOUNDS",
                    f"Ingestion delay {delay_ms:.3f}ms is outside "
                    f"[{self.ingestion_delay_min_ms}, {self.ingestion_delay_max_ms}]ms",
                    "ingestion_time",
                )
            )

        if self.state.last_event_time is not None and event_time < self.state.last_event_time:
            errors.append(
                ValidationError(
                    "EVENT_TIME_REGRESSION",
                    f"event_time {event_time.isoformat()} precedes "
                    f"{self.state.last_event_time.isoformat()}",
                    "event_time",
                )
            )
        return errors

    def _validate_causation(self, payload: dict[str, Any]) -> list[ValidationError]:
        errors: list[ValidationError] = []
        causation_id = payload.get("causation_id")
        if causation_id is not None:
            parent = self.state.event_index.get(causation_id)
            if parent is None:
                errors.append(
                    ValidationError(
                        "CAUSATION_PARENT_MISSING",
                        f"causation_id {causation_id} does not reference an accepted prior event",
                        "causation_id",
                    )
                )
        for reference_field in ("downtime_event_id", "machine_fault_event_id"):
            reference = payload.get(reference_field)
            if reference is not None and reference not in self.state.event_index:
                errors.append(
                    ValidationError(
                        "REFERENCED_EVENT_MISSING",
                        f"{reference_field}={reference} does not reference an accepted prior event",
                        reference_field,
                    )
                )
        return errors

    def _validate_correlation(self, payload: dict[str, Any]) -> list[ValidationError]:
        errors: list[ValidationError] = []
        causation_id = payload.get("causation_id")
        correlation_id = payload.get("correlation_id")
        if causation_id and causation_id in self.state.event_correlations:
            parent_correlation = self.state.event_correlations[causation_id]
            if parent_correlation != correlation_id:
                errors.append(
                    ValidationError(
                        "CORRELATION_MISMATCH",
                        f"Child correlation_id={correlation_id} does not match "
                        f"parent correlation_id={parent_correlation}",
                        "correlation_id",
                    )
                )
        return errors

    def _validate_scenario_lineage(self, payload: dict[str, Any]) -> list[ValidationError]:
        errors: list[ValidationError] = []
        scenario_instance_id = payload.get("scenario_instance_id")
        scenario_id = payload.get("scenario_id")
        if scenario_instance_id and not scenario_id:
            errors.append(
                ValidationError(
                    "SCENARIO_ID_MISSING",
                    "scenario_id is required when scenario_instance_id is present",
                    "scenario_id",
                )
            )
        return errors

    def _validate_business_rules(self, payload: dict[str, Any]) -> list[ValidationError]:
        errors: list[ValidationError] = []
        actual = payload.get("actual_quantity")
        good = payload.get("good_quantity")
        rejected = payload.get("rejected_quantity")
        if actual is not None and good is not None and rejected is not None:
            if good < 0 or rejected < 0 or actual < 0:
                errors.append(
                    ValidationError(
                        "NEGATIVE_PRODUCTION_QUANTITY",
                        "Production quantities cannot be negative",
                        "actual_quantity",
                    )
                )
            elif good + rejected > actual + 1e-9:
                errors.append(
                    ValidationError(
                        "PRODUCTION_QUANTITY_INVARIANT",
                        "good_quantity + rejected_quantity cannot exceed actual_quantity",
                    )
                )

        event_type = payload.get("event_type")
        if event_type == "StateChanged":
            previous = payload.get("previous_state")
            new = payload.get("new_state")
            if previous == new:
                errors.append(
                    ValidationError(
                        "NO_STATE_CHANGE",
                        "StateChanged must change machine state",
                        "new_state",
                    )
                )

        if event_type == "ProductionLossRecorded":
            loss_quantity = payload.get("loss_quantity")
            if loss_quantity is not None and loss_quantity < 0:
                errors.append(
                    ValidationError(
                        "NEGATIVE_LOSS_QUANTITY",
                        "loss_quantity cannot be negative",
                        "loss_quantity",
                    )
                )

        return errors

    def _advance_observed_cursor(self, payload: dict[str, Any]) -> None:
        sequence = payload.get("generation_sequence")
        if isinstance(sequence, int) and not isinstance(sequence, bool):
            self.state.last_seen_generation_sequence = sequence
        raw_event_time = payload.get("event_time")
        if raw_event_time:
            try:
                event_time = datetime.fromisoformat(
                    str(raw_event_time).replace("Z", "+00:00")
                )
            except ValueError:
                return
            if self.state.last_event_time is None or event_time >= self.state.last_event_time:
                self.state.last_event_time = event_time

    def _accept(self, payload: dict[str, Any]) -> None:
        event_id = payload["event_id"]
        sequence = payload["generation_sequence"]
        event_time = datetime.fromisoformat(payload["event_time"].replace("Z", "+00:00"))
        self.state.event_ids.add(event_id)
        self.state.event_index[event_id] = payload
        self.state.event_correlations[event_id] = payload.get("correlation_id")
        self.state.last_generation_sequence = sequence
        self.state.last_event_time = event_time
        self.state.valid_count += 1
