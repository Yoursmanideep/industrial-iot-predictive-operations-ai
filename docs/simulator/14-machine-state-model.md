# 14 — Machine State Model and Behavior Interfaces

## Scope

Stage 3.5.2 defines the machine state layer that all later telemetry, scenario, production, quality and maintenance behavior will use.

The source of truth for allowed operating states is the enterprise factory configuration from Stage 1.

## Machine states

RUNNING, IDLE, SETUP, STARVED, BLOCKED, FAULT, MAINTENANCE, OFFLINE and RECOVERY are explicit domain states.

These states are not telemetry-derived labels.

## Machine identity

Each machine carries machine_id, plant_id, line_id, machine_type and an optional machine_model.

The state layer represents the existing 270-machine population; it does not create additional machines.

## State transitions

A transition records machine_id, from_state, to_state, event_time, reason_code and optional correlation/causation references.

Transitions are validated against an explicit transition matrix.

Same-state transitions are rejected.

Transition event_time also cannot precede the machine's existing state_since timestamp.

## Behavior interface

All machine-specific implementations satisfy one common evaluate operation.

The behavior context provides simulation elapsed time, workload factor, ambient temperature, machine health factor and optional scenario stage.

The behavior output provides recommended state, production eligibility, telemetry interval and signal inputs.

This separates generic simulation orchestration from machine-type-specific behavior.

## Type profiles

Nine machine types are configured: CNC, HYDRAULIC_PRESS, INDUSTRIAL_ROBOT, CONVEYOR, COMPRESSOR, FURNACE, INSPECTION, PACKAGING and PALLETIZER.

Each profile uses the telemetry signal names already defined by the Stage 2.2 machine telemetry contract.

Each profile also defines production-eligible states, telemetry-enabled states, live telemetry interval, workload ceiling and minimum health threshold.

The live default interval is five seconds. Historical bootstrap compaction remains controlled by the Stage 3.4 generation contract.

## Registry

MachineBehaviorRegistry maps machine_type to a behavior implementation.

Stage 3.5.2 supplies a generic implementation for every configured type. It evaluates eligibility only; it does not yet generate physical signal values.

Type-specific physics are intentionally deferred to the next stage.

## Separation of concerns

Machine state is separate from scenario progression, telemetry generation, production execution, quality outcomes and maintenance workflows.

This keeps state transitions explicit and auditable.

## Verification

Stage 3.5.2 verification covers:

- all nine factory states
- valid and invalid transitions
- protection against backward simulation time
- all nine machine-type profiles
- exact profile-to-telemetry-catalog signal alignment
- behavior registration for every machine type
- production eligibility evaluation
- machine state snapshot schema

## Next stage

Stage 3.5.3 — Type-specific machine behavior and telemetry physics.