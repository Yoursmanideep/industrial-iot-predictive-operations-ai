from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from industrial_sim.domain.scenario import ScenarioDefinition


class ScenarioCatalogError(ValueError):
    """Raised when the governed scenario catalog is invalid."""


class ScenarioCatalog:
    def __init__(self, definitions: dict[str, ScenarioDefinition]) -> None:
        self._definitions = definitions

    @property
    def definitions(self) -> dict[str, ScenarioDefinition]:
        return dict(self._definitions)

    def get(self, scenario_id: str) -> ScenarioDefinition:
        try:
            return self._definitions[scenario_id]
        except KeyError as exc:
            raise ScenarioCatalogError(
                f"Unknown scenario_id: {scenario_id}"
            ) from exc

    def for_machine_type(self, machine_type_code: str) -> tuple[ScenarioDefinition, ...]:
        return tuple(
            definition
            for definition in self._definitions.values()
            if definition.machine_type_code == machine_type_code
        )


def load_scenario_catalog(path: str | Path) -> ScenarioCatalog:
    config_path = Path(path)
    if not config_path.is_file():
        raise ScenarioCatalogError(f"Scenario catalog not found: {config_path}")

    try:
        document: Any = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ScenarioCatalogError(f"Invalid YAML: {config_path}") from exc

    if not isinstance(document, dict) or not isinstance(document.get("scenarios"), list):
        raise ScenarioCatalogError("Scenario catalog must contain a scenarios list")

    definitions: dict[str, ScenarioDefinition] = {}
    for raw in document["scenarios"]:
        if not isinstance(raw, dict):
            raise ScenarioCatalogError("Each scenario entry must be a mapping")
        scenario_id = str(raw["scenario_id"])
        if scenario_id in definitions:
            raise ScenarioCatalogError(f"Duplicate scenario_id: {scenario_id}")

        progression = raw.get("progression_minutes")
        if not isinstance(progression, list) or len(progression) != 2:
            raise ScenarioCatalogError(
                f"{scenario_id} must define progression_minutes as [min, max]"
            )

        definitions[scenario_id] = ScenarioDefinition(
            scenario_id=scenario_id,
            failure_mode_code=str(raw["failure_mode_code"]),
            machine_type_code=str(raw["machine_type_code"]),
            description=str(raw["description"]),
            trigger=str(raw["trigger"]),
            progression_min_minutes=int(progression[0]),
            progression_max_minutes=int(progression[1]),
            affected_signals=tuple(raw.get("affected_signals", [])),
            behavior=dict(raw.get("behavior", {})),
            production_effect=raw.get("production_effect"),
            maintenance_type=raw.get("maintenance_type"),
        )

    return ScenarioCatalog(definitions)
