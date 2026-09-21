from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from industrial_sim.domain.scenario import ScenarioProgress, ScenarioStage, ScenarioStatus
from industrial_sim.scenarios.catalog import load_scenario_catalog
from industrial_sim.scenarios.effects import ScenarioTelemetryEffectEngine

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
EVENT_TIME = datetime(2026, 9, 21, 6, 0, tzinfo=timezone.utc)
INSTANCE_ID = str(UUID("12345678-1234-5678-1234-567812345678"))


def progress(severity: float) -> ScenarioProgress:
    return ScenarioProgress(
        scenario_instance_id=UUID(INSTANCE_ID),
        stage=ScenarioStage.CRITICAL,
        status=ScenarioStatus.ACTIVE,
        severity=severity,
        normalized_progress=severity,
        production_multiplier=1.0,
        quality_multiplier=1.0,
        terminal=False,
    )


def test_bearing_scenario_applies_catalog_driven_effects() -> None:
    catalog = load_scenario_catalog(CONFIG_DIR / "scenario_catalog.yaml")
    definition = catalog.get("SCN-CNC-BRG")
    engine = ScenarioTelemetryEffectEngine()
    baseline = {
        "vibration_mm_s": 2.0,
        "temperature_c": 40.0,
        "power_kw": 30.0,
        "spindle_rpm": 4000.0,
        "quality_score_pct": 99.0,
    }

    result = engine.apply(
        baseline,
        definition,
        INSTANCE_ID,
        0.8,
        EVENT_TIME,
    )

    assert result["vibration_mm_s"] > baseline["vibration_mm_s"]
    assert result["temperature_c"] > baseline["temperature_c"]
    assert result["power_kw"] > baseline["power_kw"]
    assert result["quality_score_pct"] < baseline["quality_score_pct"]


def test_zero_severity_preserves_baseline() -> None:
    catalog = load_scenario_catalog(CONFIG_DIR / "scenario_catalog.yaml")
    definition = catalog.get("SCN-CNC-BRG")
    engine = ScenarioTelemetryEffectEngine()
    baseline = {"vibration_mm_s": 2.0, "temperature_c": 40.0, "power_kw": 30.0, "spindle_rpm": 4000.0, "quality_score_pct": 99.0}

    result = engine.apply(baseline, definition, INSTANCE_ID, 0.0, EVENT_TIME)
    assert result == baseline
