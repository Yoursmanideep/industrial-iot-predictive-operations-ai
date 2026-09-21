# 17 — Scenario Execution Engine and Degradation State Progression

## Scope

Stage 3.5.5 turns the Stage 3.3 scenario catalog into executable, deterministic scenario instances.

The engine is generic: failure-specific definitions remain in config/scenario_catalog.yaml.

## Scenario instance

A ScenarioInstance binds one catalog scenario to one machine and one simulation run.

It carries the run ID, machine ID, failure mode, start/end times, lifecycle stage, status, optional intervention/failure references, correlation ID and generation sequence.

## Deterministic identity and duration

Scenario-instance IDs are derived deterministically from simulator run ID, machine ID, scenario ID, start time and generation sequence.

Progression duration is also deterministically selected within the minimum and maximum duration defined by the scenario catalog.

This allows the same run to be replayed without changing scenario identity or duration.

## Progression

The active degradation portion is divided into four deterministic bands:

- 0–25%: EARLY_DEGRADATION
- 25–55%: ANOMALY
- 55–80%: CRITICAL
- 80–100%: FAILURE

Normalized progress is transformed into a severity value from 0 to 1.

The current generic production effect decreases production capacity as severity grows, with failure removing production capacity.

The current generic quality effect decreases quality multiplier as severity grows.

Later type-specific scenario effects can refine those generic multipliers using the affected_signals and behavior metadata already present in the catalog.

## Predictive intervention

An active scenario can be interrupted during EARLY_DEGRADATION, ANOMALY or CRITICAL.

Intervention transitions the scenario to MAINTENANCE and records the intervention event ID. The status becomes AVOIDED, providing a ground-truth avoided-failure outcome.

## Failure path

When planned scenario duration is reached, the stage becomes FAILURE and status becomes FAILED.

The scenario can then be routed through maintenance and recovery.

## Corrective maintenance and recovery

A failed scenario moves through an explicit corrective-maintenance transition:

FAILURE → MAINTENANCE → RECOVERY → BASELINE.

The engine exposes this as begin_maintenance(), complete_maintenance() and complete_recovery(). Tests do not bypass these transitions by directly mutating stage.

Completing recovery sets the scenario status to RESOLVED.

The scenario engine does not itself mutate the Machine domain state. That responsibility remains with the machine state engine and the future maintenance orchestrator.

## Causal isolation

The scenario engine produces lifecycle transitions. It does not invent AlarmRaised, MachineFaulted, ProductionLossRecorded or Maintenance events directly. Those event builders consume the scenario progression and create domain events with explicit causation/correlation relationships.

## Verification

Stage 3.5.5 tests cover all 25 scenarios, deterministic scenario IDs, catalog-bounded durations, progression thresholds, predictive intervention, failure status, maintenance and recovery transitions.

## Next stage

Stage 3.5.6 — Scenario-to-machine telemetry effects and operational event generation.
