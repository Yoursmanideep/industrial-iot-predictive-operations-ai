from __future__ import annotations

from dataclasses import dataclass

from industrial_sim.domain.production import LineCapacitySnapshot, ProductionBatch
from industrial_sim.context.production_context import ProductionContext


@dataclass(frozen=True)
class MachineExecutionInput:
    machine_id: str
    machine_type: str
    effective_capacity_units_min: float
    available: bool = True
    scenario_production_multiplier: float = 1.0
    quality_multiplier: float = 1.0


@dataclass(frozen=True)
class LineExecutionResult:
    line_id: str
    available: bool
    bottleneck_rate_units_min: float
    produced_quantity: float
    good_quantity: float
    rejected_quantity: float
    machine_ids: tuple[str, ...]
    blocked_machine_ids: tuple[str, ...]
    loss_category: str | None = None
    loss_reason_code: str | None = None


class LineExecutionEngine:
    def __init__(self, config: dict) -> None:
        self._cfg = config["line_execution"]
        self._loss_cfg = config["losses"]

    def snapshot(self, line_id: str, event_time, machines: tuple[MachineExecutionInput, ...]) -> LineCapacitySnapshot:
        available = tuple(m for m in machines if m.available)
        blocked = tuple(m.machine_id for m in machines if not m.available)
        if not available or blocked:
            return LineCapacitySnapshot(
                line_id=line_id,
                event_time=event_time,
                bottleneck_rate_units_min=0.0,
                available=False,
                active_machine_ids=tuple(m.machine_id for m in available),
                blocked_machine_ids=blocked,
                scenario_multiplier=0.0,
            )
        bottleneck = min(
            m.effective_capacity_units_min * max(0.0, min(1.0, m.scenario_production_multiplier))
            for m in available
        )
        return LineCapacitySnapshot(
            line_id=line_id,
            event_time=event_time,
            bottleneck_rate_units_min=bottleneck,
            available=bottleneck > 0,
            active_machine_ids=tuple(m.machine_id for m in available),
            blocked_machine_ids=blocked,
            scenario_multiplier=1.0 if bottleneck > 0 else 0.0,
        )

    def advance_batch(self, batch: ProductionBatch, snapshot: LineCapacitySnapshot, context: ProductionContext, elapsed_seconds: float, quality_multiplier: float) -> LineExecutionResult:
        if elapsed_seconds < 0:
            raise ValueError("elapsed_seconds cannot be negative")
        if not snapshot.available or batch.remaining_quantity <= 0:
            return LineExecutionResult(snapshot.line_id, False, 0.0, 0.0, 0.0, 0.0, snapshot.active_machine_ids, snapshot.blocked_machine_ids, "DOWNTIME", "MACHINE_DOWNTIME")

        rate = snapshot.bottleneck_rate_units_min
        produced = min(batch.remaining_quantity, rate * elapsed_seconds / 60.0)
        quality = max(0.0, min(1.0, quality_multiplier))
        rejected = produced * (1.0 - quality)
        good = produced - rejected
        baseline_capacity = max(rate, 0.01)
        ratio = rate / baseline_capacity
        loss_category = None
        loss_reason = None
        if produced > 0 and ratio < float(self._loss_cfg["slowdown_threshold_ratio"]):
            loss_category = "SLOWDOWN"
            loss_reason = self._loss_cfg["default_loss_reasons"]["slowdown"]
        return LineExecutionResult(snapshot.line_id, True, rate, produced, good, rejected, snapshot.active_machine_ids, snapshot.blocked_machine_ids, loss_category, loss_reason)