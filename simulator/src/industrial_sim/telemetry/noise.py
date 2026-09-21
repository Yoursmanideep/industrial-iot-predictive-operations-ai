from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DeterministicNoise:
    """Stable per-machine/per-time noise; avoids a mutable global random stream."""

    namespace: str
    machine_id: str
    event_time: datetime

    def _rng(self, signal: str) -> random.Random:
        raw = "|".join(
            (self.namespace, self.machine_id, self.event_time.isoformat(), signal)
        ).encode("utf-8")
        seed = int.from_bytes(hashlib.sha256(raw).digest()[:8], "big")
        return random.Random(seed)

    def gaussian(
        self,
        signal: str,
        mean: float = 0.0,
        stddev: float = 1.0,
    ) -> float:
        return self._rng(signal).gauss(mean, stddev)

    def uniform(
        self,
        signal: str,
        low: float = 0.0,
        high: float = 1.0,
    ) -> float:
        return self._rng(signal).uniform(low, high)


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))


def load_factor(value: float) -> float:
    return clamp(value, 0.0, 1.25)


def degradation_factor(health_factor: float, scenario_severity: float) -> float:
    return clamp(max(1.0 - health_factor, scenario_severity), 0.0, 1.0)


def ambient_delta(ambient_temperature_c: float) -> float:
    return ambient_temperature_c - 27.0


def running_scale(state: str) -> float:
    return 1.0 if state == "RUNNING" else 0.0
