from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class MachineProfileError(ValueError):
    """Raised when machine behavior profiles are invalid."""


@dataclass(frozen=True)
class MachineTypeProfile:
    machine_type: str
    code: str
    telemetry_signals: tuple[str, ...]
    productive_states: frozenset[str]
    telemetry_states: frozenset[str]
    default_telemetry_interval_seconds: int
    max_workload_factor: float
    minimum_health_factor: float


@dataclass(frozen=True)
class MachineProfileCatalog:
    profiles: dict[str, MachineTypeProfile]

    def get(self, machine_type: str) -> MachineTypeProfile:
        try:
            return self.profiles[machine_type]
        except KeyError as exc:
            raise MachineProfileError(
                f"Unknown machine_type: {machine_type}"
            ) from exc


def load_machine_profiles(path: str | Path) -> MachineProfileCatalog:
    config_path = Path(path)
    if not config_path.is_file():
        raise MachineProfileError(f"Machine profile file not found: {config_path}")

    try:
        with config_path.open("r", encoding="utf-8") as handle:
            document: Any = yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise MachineProfileError(f"Invalid machine profile YAML: {config_path}") from exc

    if not isinstance(document, dict):
        raise MachineProfileError("Machine profile document must be a mapping.")

    entries = document.get("profiles")
    if not isinstance(entries, dict):
        raise MachineProfileError("Missing 'profiles' mapping.")

    profiles: dict[str, MachineTypeProfile] = {}
    for machine_type, entry in entries.items():
        if not isinstance(entry, dict):
            raise MachineProfileError(f"Profile {machine_type} must be a mapping.")

        required = (
            "code",
            "telemetry_signals",
            "productive_states",
            "telemetry_states",
            "default_telemetry_interval_seconds",
            "max_workload_factor",
            "minimum_health_factor",
        )
        missing = [key for key in required if key not in entry]
        if missing:
            raise MachineProfileError(
                f"Profile {machine_type} missing: {', '.join(missing)}"
            )

        interval = entry["default_telemetry_interval_seconds"]
        max_workload = entry["max_workload_factor"]
        min_health = entry["minimum_health_factor"]
        if not isinstance(interval, int) or interval <= 0:
            raise MachineProfileError(
                f"{machine_type}.default_telemetry_interval_seconds must be positive."
            )
        if not isinstance(max_workload, (int, float)) or max_workload <= 0:
            raise MachineProfileError(
                f"{machine_type}.max_workload_factor must be positive."
            )
        if not isinstance(min_health, (int, float)) or not 0 <= min_health <= 1:
            raise MachineProfileError(
                f"{machine_type}.minimum_health_factor must be in [0, 1]."
            )

        profiles[machine_type] = MachineTypeProfile(
            machine_type=machine_type,
            code=str(entry["code"]),
            telemetry_signals=tuple(entry["telemetry_signals"]),
            productive_states=frozenset(entry["productive_states"]),
            telemetry_states=frozenset(entry["telemetry_states"]),
            default_telemetry_interval_seconds=interval,
            max_workload_factor=float(max_workload),
            minimum_health_factor=float(min_health),
        )

    return MachineProfileCatalog(profiles)
