# 18 — Scenario Effects and Operational Event Generation

## Scope

Stage 3.5.6 connects executable scenario progression to telemetry and operational events.

## Scenario-to-telemetry flow

The flow is:

ScenarioInstance
→ ScenarioProgress
→ base machine physics
→ scenario-specific effect engine
→ final telemetry

The scenario catalog remains the source of truth for affected signals and behavior direction.

The effect engine applies controlled adjustments to the affected signals only.

## Correlation rules

Scenario severity is the normalized scenario progress.

Severity is propagated into telemetry generation as a scenario context rather than mutating the machine state directly.

The machine state engine remains authoritative for state changes.

## Operational events

Scenario progression creates operational events at discrete boundaries.

ANOMALY and CRITICAL create AlarmRaised events.

FAILURE creates MachineFaulted followed by StateChanged to FAULT.

MAINTENANCE clears the active scenario alarm when one exists and creates MachineStopped with MAINTENANCE as the new state.

RECOVERY creates MachineRecovered with RECOVERY as the new state.

BASELINE creates StateChanged to RUNNING.

## Causal lineage

The operational event engine preserves immediate causation:

AlarmRaised
→ MachineFaulted
→ StateChanged

A maintenance transition can be caused by the predictive-intervention event or the latest fault.

Recovery is caused by the maintenance event.

Return to baseline is caused by the recovery event.

Every generated operational event also carries simulator run, scenario and generation lineage.

## Controlled alarm vocabulary

The simulator uses the existing reference alarm families:

- VIBRATION_HIGH
- TEMPERATURE_HIGH
- PRESSURE_LOW
- POWER_ABNORMAL
- QUALITY_DEGRADATION
- COMMUNICATION_LOST

Signals such as torque, cycle time, measurement deviation and fuel flow are mapped to the nearest governed alarm family through config/simulator_alarm_mapping.yaml.

The simulator does not create ungoverned alarm codes.

## Deterministic IDs

Operational event IDs are derived from simulator run, machine, event type, event time and generation sequence.

The same inputs produce the same event ID.

Scenario instance IDs are separately deterministic from the scenario-instance generation key.

## Failure and avoided-failure paths

Two ground-truth paths now exist:

Failure:
scenario progression reaches FAILURE and emits fault/state events.

Avoided failure:
predictive intervention during degradation moves the scenario to MAINTENANCE without reaching FAILURE.

These paths are later usable for model labels such as failure and avoided failure.

## Contract alignment

The Stage 3.5.6 layer uses the existing machine operational-event schema and machine telemetry schema.

The earlier correction of Conveyor and Packaging throughput naming remains part of the canonical telemetry contract.

## Verification

Tests cover:

- scenario-specific telemetry effects
- deterministic effect behavior
- full alarm → fault → state-change causal chain
- avoided-failure maintenance transition
- deterministic operational event IDs
- intervention causation
- recovery and baseline lineage

## Next stage

Stage 3.6 — Production order, batch and line execution engine.
