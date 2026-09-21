from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

from industrial_sim.domain.scenario import ScenarioDefinition
from industrial_sim.telemetry.noise import DeterministicNoise


@dataclass(frozen=True)
class ScenarioTelemetryEffect:
    scenario_id: str
    scenario_instance_id: str
    severity: float
    event_time: datetime


class ScenarioTelemetryEffectEngine:
    def apply(
        self,
        baseline: dict[str, float],
        definition: ScenarioDefinition,
        instance_id: str,
        severity: float,
        event_time: datetime,
    ) -> dict[str, float]:
        if not 0 <= severity <= 1:
            raise ValueError("severity must be in [0, 1]")
        result = dict(baseline)
        effect = ScenarioTelemetryEffect(
            scenario_id=definition.scenario_id,
            scenario_instance_id=instance_id,
            severity=severity,
            event_time=event_time,
        )
        noise = DeterministicNoise(
            f"scenario-effect:{effect.scenario_id}",
            effect.scenario_instance_id,
            event_time,
        )

        for signal in definition.affected_signals:
            if signal not in result:
                continue
            behavior = self._behavior_for_signal(signal, definition.behavior)
            result[signal] = self._transform(
                result[signal],
                behavior,
                severity,
                signal,
                noise,
            )
        return result

    @staticmethod
    def _behavior_for_signal(signal: str, behavior: dict[str, str]) -> str | None:
        aliases = {
            "temperature": "temperature",
            "motor_temperature": "temperature",
            "chamber_temperature": "temperature",
            "equipment_temperature": "temperature",
            "vibration": "vibration",
            "power": "power",
            "rpm": "rpm",
            "spindle_rpm": "rpm",
            "pressure": "pressure",
            "hydraulic_pressure": "pressure",
            "discharge_pressure": "pressure",
            "pressure_mbar": "pressure",
            "force": "force",
            "torque": "torque",
            "cycle_time": "cycle_time",
            "production_rate": "production",
            "throughput": "throughput",
            "quality": "quality",
            "position_error": "position_error",
            "measurement_deviation": "measurement_deviation",
            "fuel_flow_rate": "fuel_flow_rate",
            "belt_speed": "belt_speed",
            "inspection_cycle_time": "inspection_cycle_time",
        }
        token = aliases.get(signal)
        if token is None:
            token = next(
                (candidate for candidate in aliases.values() if candidate in signal),
                None,
            )
        if token is None:
            return next(iter(behavior.values()), None)
        for key, value in behavior.items():
            normalized_key = key.replace("_trend", "").replace("_stability", "")
            if token in normalized_key or normalized_key in token:
                return str(value)
        return next(iter(behavior.values()), None)

    @staticmethod
    def _transform(
        value: float,
        behavior: str | None,
        severity: float,
        signal: str,
        noise: DeterministicNoise,
    ) -> float:
        if behavior is None:
            return value
        normalized = behavior.lower()
        magnitude = {
            "increasing": 0.18,
            "gradual_increase": 0.15,
            "moderate_increase": 0.22,
            "sharp_increase": 0.38,
            "decreasing": 0.18,
            "gradual_decrease": 0.15,
            "sharp_decrease": 0.38,
        }
        if normalized in magnitude:
            coefficient = magnitude[normalized]
            direction = 1.0 if "increase" in normalized or normalized == "increasing" else -1.0
            return max(0.0, value * (1.0 + direction * coefficient * severity))

        if normalized == "oscillatory_increase":
            phase = 2.0 * math.pi * noise.uniform(f"phase:{signal}")
            envelope = 0.12 * severity + 0.08 * severity * math.sin(phase)
            return max(0.0, value * (1.0 + envelope))

        if normalized == "increasing" and "variance" in signal:
            return max(0.0, value)

        if "variance" in normalized:
            disturbance = noise.gaussian(f"variance:{signal}", stddev=0.12 * severity)
            return max(0.0, value * (1.0 + disturbance))

        if normalized == "decreasing" or "decreasing_stability" in normalized:
            return max(0.0, value * (1.0 - 0.18 * severity))

        return value


def apply_scenario_effects(
    baseline: dict[str, float],
    definition: ScenarioDefinition,
    instance_id: str,
    severity: float,
    event_time: datetime,
) -> dict[str, float]:
    return ScenarioTelemetryEffectEngine().apply(
        baseline,
        definition,
        instance_id,
        severity,
        event_time,
    )
