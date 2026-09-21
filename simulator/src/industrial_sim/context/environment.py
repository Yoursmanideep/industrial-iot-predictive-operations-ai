from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class EnvironmentReading:
    plant_id: str
    event_time_utc: datetime
    ambient_temperature_c: float
    utility_power_factor: float
    utility_interruption_active: bool


class EnvironmentModel:
    def __init__(self, config: dict) -> None:
        self._config = config["environment"]

    def reading(self, plant_id: str, event_time: datetime) -> EnvironmentReading:
        event_time_utc = event_time.astimezone(timezone.utc)
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        days = (event_time_utc - epoch).total_seconds() / 86400.0
        hour_fraction = event_time_utc.hour + event_time_utc.minute / 60.0
        hour_angle = 2.0 * math.pi * hour_fraction / 24.0
        seasonal_period = float(
            self._config["ambient_temperature_c"]["seasonal_period_days"]
        )
        seasonal_angle = 2.0 * math.pi * (days / seasonal_period)

        ambient_cfg = self._config["ambient_temperature_c"]
        plant_offset = float(ambient_cfg["plant_offsets_c"].get(plant_id, 0.0))
        temperature = (
            float(ambient_cfg["baseline_c"])
            + float(ambient_cfg["daily_amplitude_c"])
            * math.sin(hour_angle - math.pi / 2.0)
            + float(ambient_cfg["seasonal_amplitude_c"])
            * math.sin(seasonal_angle)
            + plant_offset
            + self._machine_variation(plant_id, event_time_utc)
        )

        utility_cfg = self._config["utility"]
        variation_pct = float(utility_cfg["normal_variation_pct"])
        variation = (
            self._deterministic_unit("utility", plant_id, event_time_utc)
            * 2.0
            * variation_pct
            / 100.0
            - variation_pct / 100.0
        )
        interruption = self._utility_interruption(
            plant_id,
            event_time_utc,
            utility_cfg,
        )
        power_factor = 0.0 if interruption else max(
            0.85,
            min(1.05, float(utility_cfg["nominal_power_factor"]) + variation),
        )

        return EnvironmentReading(
            plant_id=plant_id,
            event_time_utc=event_time_utc,
            ambient_temperature_c=temperature,
            utility_power_factor=power_factor,
            utility_interruption_active=interruption,
        )

    def _machine_variation(self, plant_id: str, event_time: datetime) -> float:
        amplitude = float(
            self._config["ambient_temperature_c"]["machine_local_variation_c"]
        )
        return (
            self._deterministic_unit("ambient", plant_id, event_time) * 2.0 - 1.0
        ) * amplitude

    @staticmethod
    def _utility_interruption(
        plant_id: str,
        event_time: datetime,
        utility_cfg: dict,
    ) -> bool:
        probability = float(utility_cfg["interruption_probability_per_hour"])
        hour_key = event_time.replace(minute=0, second=0, microsecond=0)
        trigger = EnvironmentModel._deterministic_unit(
            "utility_interruption",
            plant_id,
            hour_key,
        )
        if trigger >= probability:
            return False

        duration_min, duration_max = utility_cfg["interruption_duration_seconds_range"]
        duration_span = max(0, int(duration_max) - int(duration_min))
        duration = int(duration_min) + int(
            EnvironmentModel._deterministic_unit(
                "utility_interruption_duration",
                plant_id,
                hour_key,
            )
            * (duration_span + 1)
        )
        elapsed = int((event_time - hour_key).total_seconds())
        return elapsed < duration

    @staticmethod
    def _deterministic_unit(
        namespace: str,
        plant_id: str,
        event_time: datetime,
    ) -> float:
        raw = f"{namespace}|{plant_id}|{event_time.isoformat()}".encode("utf-8")
        integer = int.from_bytes(hashlib.sha256(raw).digest()[:8], "big")
        return integer / float(2**64 - 1)
