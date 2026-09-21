from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math

from industrial_sim.context.shift import ShiftContext


@dataclass(frozen=True)
class WorkloadInputs:
    rated_capacity_units_min: float
    product_cycle_time_seconds: float
    machine_health_factor: float
    machine_age_years: float
    state: str
    product_mix_factor: float = 0.0
    changeover_active: bool = False


@dataclass(frozen=True)
class WorkloadResult:
    workload_factor: float
    line_utilization: float
    effective_capacity_units_min: float
    changeover_penalty: float
    age_penalty: float
    health_penalty: float


class WorkloadModel:
    def __init__(self, config: dict) -> None:
        self._cfg = config["workload"]

    def evaluate(self, inputs: WorkloadInputs, shift: ShiftContext, event_time: datetime) -> WorkloadResult:
        if event_time.tzinfo is None:
            raise ValueError("event_time must be timezone-aware.")
        base = float(self._cfg["base_line_utilization"])
        mix = max(-0.12, min(0.12, inputs.product_mix_factor))
        shift_adjusted = base * shift.workload_multiplier
        age_penalty = self._age_penalty(inputs.machine_age_years)
        health_penalty = self._health_penalty(inputs.machine_health_factor)
        changeover_penalty = 0.88 if inputs.changeover_active else 1.0

        circadian = 0.04 * math.sin(2.0 * math.pi * event_time.hour / 24.0)
        state_factor = {
            "RUNNING": 1.0,
            "IDLE": 0.10,
            "SETUP": 0.55,
            "STARVED": 0.40,
            "BLOCKED": 0.35,
            "FAULT": 0.0,
            "MAINTENANCE": 0.0,
            "OFFLINE": 0.0,
            "RECOVERY": 0.35,
        }[inputs.state]

        workload = shift_adjusted * (1.0 + mix + circadian)
        workload *= (1.0 - age_penalty) * (1.0 - health_penalty) * changeover_penalty * state_factor
        workload = max(float(self._cfg["minimum_factor"]), min(workload, float(self._cfg["maximum_factor"])))

        rated_capacity = max(0.0, inputs.rated_capacity_units_min)
        cycle_capacity = 60.0 / max(inputs.product_cycle_time_seconds, 1.0)
        effective_capacity = min(rated_capacity, cycle_capacity)
        effective_capacity *= (1.0 - age_penalty) * (1.0 - health_penalty)

        return WorkloadResult(
            workload_factor=workload,
            line_utilization=max(0.0, min(1.0, workload / max(float(self._cfg["maximum_factor"]), 1.0))),
            effective_capacity_units_min=effective_capacity,
            changeover_penalty=changeover_penalty,
            age_penalty=age_penalty,
            health_penalty=health_penalty,
        )

    def _age_penalty(self, age_years: float) -> float:
        cfg = self._cfg["machine_age_effect"]
        if not cfg["enabled"]:
            return 0.0
        reference = float(cfg["reference_age_years"])
        return min(float(cfg["maximum_penalty"]), max(0.0, age_years - reference) / max(reference, 1.0) * float(cfg["maximum_penalty"]))

    def _health_penalty(self, health_factor: float) -> float:
        cfg = self._cfg["health_effect"]
        if health_factor >= float(cfg["full_health_factor"]):
            return 0.0
        minimum = float(cfg["minimum_health_factor"])
        relative = 1.0 - max(minimum, health_factor)
        return min(float(cfg["maximum_penalty"]), relative * float(cfg["maximum_penalty"]) / max(1.0 - minimum, 0.01))
