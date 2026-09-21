from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class ConfigurationError(ValueError):
    """Raised when simulator configuration cannot be loaded or validated."""


@dataclass(frozen=True)
class GenerationContract:
    contract_version: str
    default_seed: int
    default_timezone: str
    canonical_timestamp_timezone: str
    raw: dict[str, Any]


def load_generation_contract(path: str | Path) -> GenerationContract:
    """Load and minimally validate the Stage 3.4 generation contract."""
    config_path = Path(path)
    if not config_path.is_file():
        raise ConfigurationError(f"Configuration file not found: {config_path}")

    try:
        with config_path.open("r", encoding="utf-8") as handle:
            document = yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise ConfigurationError(
            f"Invalid YAML in configuration file: {config_path}"
        ) from exc

    if not isinstance(document, dict):
        raise ConfigurationError("Generation contract must be a YAML mapping.")

    generation = document.get("generation")
    if not isinstance(generation, dict):
        raise ConfigurationError("Missing 'generation' mapping.")

    required = (
        "contract_version",
        "default_seed",
        "default_timezone",
        "canonical_timestamp_timezone",
    )
    missing = [key for key in required if key not in generation]
    if missing:
        raise ConfigurationError(
            f"Missing generation fields: {', '.join(missing)}"
        )

    seed = generation["default_seed"]
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise ConfigurationError("generation.default_seed must be a non-negative integer.")

    return GenerationContract(
        contract_version=str(generation["contract_version"]),
        default_seed=seed,
        default_timezone=str(generation["default_timezone"]),
        canonical_timestamp_timezone=str(
            generation["canonical_timestamp_timezone"]
        ),
        raw=document,
    )
