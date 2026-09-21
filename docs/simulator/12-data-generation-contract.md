# 12 — Simulator Data-Generation Contract

## Purpose

Stage 3.4 defines the exact mechanics by which the simulator converts the Stage 3.1–3.3 enterprise definitions into reproducible synthetic history and streaming events.

The simulator is a stateful event engine. Machine state, workload, degradation, production, quality and maintenance interact over simulation time.

## 1. Simulation modes

| Mode | Purpose | Baseline telemetry | Incident telemetry |
|---|---|---:|---:|
| BOOTSTRAP | Build historical context | 60 seconds | 5 seconds |
| BACKFILL | Generate a defined historical window | 60 seconds | 5 seconds |
| LIVE | Advance continuously | 5 seconds | 5 seconds |
| REPLAY | Reproduce a prior run | Same as source | Same as source |

The 180-day bootstrap history uses one-minute baseline telemetry to control synthetic data volume. Five-second telemetry is reserved for degradation, incident and recovery windows where high-resolution signal behavior matters most.

## 2. Run identity

Every execution has:

```text
simulator_run_id
run_mode
generator_version
configuration_version
deterministic_seed
simulation_start_time
simulation_end_time
```

A REPLAY run additionally references source_run_id.

## 3. Deterministic identity

Reproducible entities and events use UUIDv5-style deterministic derivation from a simulator-run namespace and stable generation inputs.

Event identity uses the logical key:

```text
simulator_run_id
+ entity_business_key
+ event_type
+ event_time
+ generation_sequence
```

Same run + same seed + same configuration must reproduce the same identifiers.

A different run ID intentionally generates different identifiers.

## 4. Generation sequence

Every generated record receives a monotonically increasing generation_sequence scoped to the simulation run.

Ordering rules:

1. event_time
2. generation_sequence
3. event_id

This gives deterministic ordering when multiple events share the same event time.

## 5. Simulator trace metadata

Simulator-generated events can carry the following lineage fields:

```text
simulator_run_id
scenario_id
scenario_instance_id
generated_at_utc
deterministic_seed
generation_sequence
generator_version
configuration_version
```

The event contracts were extended to accept these fields explicitly, so simulator trace data is not treated as an undeclared payload extension.

## 6. Entity generation order

```text
Simulator Run
    ↓
Plants
    ↓
Production Areas
    ↓
Lines
    ↓
Machine Models
    ↓
Machines
    ↓
Products / People / Suppliers / Parts
    ↓
Production Orders
    ↓
Batches
    ↓
Scenario Instances
    ↓
Events
```

An event cannot be generated against a reference entity that has not yet been initialized.

## 7. Bootstrap history

All 270 machines participate in the 180-day historical context.

The bootstrap contains:

- normal production
- idle and setup periods
- planned maintenance
- communication interruptions
- controlled degradation
- failure episodes
- successful predictive interventions
- quality variation
- production losses

This provides both healthy and degraded examples before live simulation begins.

## 8. Multi-resolution telemetry

```text
Baseline history       → 1 observation / machine / minute
Incident and recovery  → 1 observation / machine / 5 seconds
Live operation         → 1 observation / active telemetry machine / 5 seconds
```

This is a deliberate scale decision, not a change to the canonical telemetry event contract.

## 9. Production generation

Production orders are generated from plant, line capacity, product mix, shift and workload context.

Initial target:

```text
30–60 orders / plant / day
100–2500 units / order
```

Product selection is deterministic and seed-controlled.

Line assignment is capacity-aware and requires machine/product compatibility.

## 10. Batch generation

Orders may contain multiple batches.

Initial configuration:

```text
1–8 batches / order
```

Batch lineage retains production_order_id, product_id, operation_id and line_id when applicable.

## 11. Scenario instances

A scenario instance is one concrete execution of a scenario catalog definition against one machine.

It records:

```text
scenario_instance_id
simulator_run_id
scenario_id
machine_id
failure_mode_code
started_at
planned_end_at
actual_end_at
scenario_stage
status
trigger_type
intervention_event_id
failure_event_id
correlation_id
generation_sequence
```

Only one primary failure scenario is active on a machine at a time.

A scenario can end as RESOLVED, AVOIDED, FAILED or INTERRUPTED.

AVOIDED is used when intervention prevents the physical failure.

## 12. Per-tick orchestration

Every simulation tick follows:

```text
Advance clock
      ↓
Resolve shift and workload
      ↓
Update environment
      ↓
Advance active scenarios
      ↓
Update machine states
      ↓
Generate telemetry
      ↓
Evaluate alarms
      ↓
Generate operational events
      ↓
Update production
      ↓
Generate quality events
      ↓
Generate/update maintenance
      ↓
Finalize traceability
      ↓
Emit events
```

A downstream event must have an existing causal parent when causation is declared.

## 13. Telemetry generation

Telemetry is derived from:

```text
machine state
workload
product
environment
machine health
scenario stage
```

Machine-specific signal applicability remains governed by the Stage 2.2 telemetry schema.

## 14. Operational events

Operational events are emitted on discrete conditions:

- state transition
- alarm condition entry
- alarm condition exit
- fault episode
- recovery episode
- communication loss
- communication restoration

A fault event occurs once per fault episode, not once per telemetry tick.

## 15. Production events

Order and batch lifecycle events occur on business state changes.

`UnitProduced` is aggregated over 30-second windows while eligible machines are running.

Production pauses and losses are emitted when the business impact becomes measurable.

When a machine fault directly causes production loss, the production loss event carries the appropriate event linkage.

## 16. Quality events

Quality generation is inspection-driven.

Inline inspections use the configured 15-minute cadence plus batch boundaries.

Actual defect outcomes are generated independently from predicted defect probability.

Therefore:

```text
Predicted defect probability ≠ observed defect event
```

## 17. Maintenance events

Maintenance may originate from:

- predictive insight
- machine fault
- operator observation
- scheduled maintenance
- quality/inspection finding

Maintenance is lifecycle-driven.

Return to service requires explicit verification before workflow completion.

## 18. Correlation and causation

`correlation_id` groups events in one operational flow.

`causation_id` points only to the immediate parent event.

Example:

```text
AlarmRaised
    ↓
MachineFaulted
    ↓
ProductionPaused
    ↓
ProductionLossRecorded
    ↓
MaintenanceRequested
    ↓
WorkOrderCreated
    ↓
RepairCompleted
    ↓
MachineReturnedToService
```

## 19. Replay and idempotency

Replay of the same run preserves:

```text
event_id
generation_sequence
event_time
causation_id
correlation_id
scenario_instance_id
```

Replay under a new run ID generates new event IDs.

Downstream data loads remain idempotent using event_id as the logical duplicate key.

## 20. Quarantine

Generation or validation failures are not silently dropped.

A quarantined record retains:

```text
simulator_run_id
generation_sequence
raw_payload
validation_failure_reason
generated_at_utc
```

## 21. Initial synthetic calibration

Initial bootstrap target:

```text
0.35 scenario starts / 100 machine-days
```

This is a synthetic calibration parameter for project experimentation, not a claim about real industrial failure rates.

## Stage boundary

Stage 3.4 defines how the simulator generates, orders, traces, replays and validates its output.

The next stage is **Stage 3.5 — Python Simulator Architecture**, where the contract becomes the actual Python package, state engine, scenario engine, telemetry generators, event builders, validators, tests and CLI.