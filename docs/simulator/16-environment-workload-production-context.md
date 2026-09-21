# 16 — Environment, Workload, Shift and Production Context

## Scope

Stage 3.5.4 supplies the shared operating context consumed by the machine and telemetry layers.

The context engine has four layers: environment, shift, workload and production context.

## Environment

Ambient temperature is deterministic and driven by baseline, intraday cycle, seasonal cycle, plant-specific offset and bounded local variation.

Utility conditions include deterministic power-factor variation and deterministic brief interruptions. No uncontrolled global randomness is used.

## Shift

The factory schedule remains:
- SH1 06:00–14:00 local
- SH2 14:00–22:00 local
- SH3 22:00–06:00 local

Business time is resolved in Asia/Kolkata while persisted event time remains UTC.

The resolver explicitly handles the overnight third shift.

Each shift contributes a configured workload multiplier.

## Workload

Workload is derived from baseline line utilization, shift multiplier, product mix, time-of-day variation, machine age, machine health, changeover and operating state.

The resulting workload factor is bounded by the Stage 3.4 generation contract.

## Effective capacity

Effective capacity is bounded by both machine rated capacity and the theoretical capacity implied by product cycle time. Age and health penalties then reduce the result.

This makes product selection materially affect production context.

## Production context

ProductionContextEngine combines environment, shift and workload into one immutable context carrying event time, plant, line, shift, product, product cycle time, ambient temperature, utility power factor and workload result.

Later production-order and batch engines will consume this context.

## Contract alignment

The layer uses the previously defined plant IDs, line IDs, shifts and machine states. Product cycle time and machine rated capacity come from the existing reference data model.

The serializable shape is defined by simulator/schemas/production_context.schema.json.

## Verification

Tests cover all three shifts, overnight handling, deterministic environment values, plant offsets, health and age effects, non-running suppression, product cycle-time capacity impact and combined production context.

## Next stage

Stage 3.5.5 — Scenario execution engine and degradation state progression.
