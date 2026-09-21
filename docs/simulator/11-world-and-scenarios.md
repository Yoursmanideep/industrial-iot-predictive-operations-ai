# 11 — Simulator World & Scenario Model

## Purpose

This stage defines how the synthetic industrial world behaves before implementation in Python.

The simulator is a stateful event generator in which machine state, workload, degradation, production, quality and maintenance interact over simulation time.

## 1. Simulation time

The canonical platform time remains UTC while business operations use Asia/Kolkata.

Default simulation tick:

```
5 seconds
```

Telemetry is generated at the nominal five-second cadence. Operational, production, quality and maintenance events are emitted when their business conditions occur.

Each simulation run has a deterministic seed and a unique simulator_run_id.

## 2. Enterprise world

The simulation contains:

- 3 plants
- 15 production lines
- 270 machines
- 3 shifts per day
- 365-day planning horizon
- 180-day bootstrap history

Bootstrap history gives machine health and feature calculations an initial context.

## 3. Machine state model

```
OFFLINE
   ↓
IDLE
   ↓
SETUP
   ↓
RUNNING
   ├── STARVED
   ├── BLOCKED
   ├── FAULT
   └── MAINTENANCE
            ↓
         RECOVERY
            ↓
         RUNNING
```

State transitions are represented by operational events.

Telemetry does not become a substitute for explicit machine-state events.

## 4. Correlated telemetry

The core simulation rule is:

```
machine state
      +
workload
      +
product
      +
machine age
      +
environment
      +
health/degradation
      ↓
correlated telemetry
```

Signals therefore change together when the underlying operating condition changes.

Example:

```
Bearing degradation
       ↓
vibration ↑
       ↓
temperature ↑
       ↓
power ↑
       ↓
RPM stability ↓
       ↓
production rate ↓
       ↓
quality ↓
       ↓
failure
```

## 5. Production world

Production orders are generated against products and lines.

Typical lifecycle:

```
CREATED
  ↓
RELEASED
  ↓
SCHEDULED
  ↓
STARTED
  ↓
IN_PROGRESS
  ↓
PAUSED ↔ IN_PROGRESS
  ↓
COMPLETED
```

Production rate is driven by machine capacity, product cycle time, workload, health, machine state and changeover effects.

Product selection is deterministic and seed-controlled.

## 6. Quality world

Quality is generated from production conditions and inspection processes.

Important rule:

```
predicted defect probability
          ≠
actual defect outcome
```

A quality model can increase the probability of a defect, but an explicit quality event establishes the observed outcome.

This creates defensible labels for future supervised ML.

## 7. Maintenance world

Maintenance can be initiated by:

- predictive insight
- machine fault
- operator observation
- scheduled preventive maintenance
- inspection finding

Typical corrective path:

```
Failure / Prediction
       ↓
MaintenanceRequested
       ↓
WorkOrderCreated
       ↓
TechnicianAssigned
       ↓
Inspection
       ↓
Repair
       ↓
PartsConsumed
       ↓
MaintenanceVerified
       ↓
MachineReturnedToService
```

Maintenance changes machine health rather than merely producing records.

## 8. Scenario lifecycle

Each failure scenario follows:

```
BASELINE
   ↓
EARLY_DEGRADATION
   ↓
ANOMALY
   ↓
CRITICAL
   ↓
FAILURE
   ↓
MAINTENANCE
   ↓
RECOVERY
   ↓
BASELINE
```

Not every scenario has to reach FAILURE.

A predictive intervention can terminate an ongoing degradation scenario earlier.

This produces both failure cases and successful early-intervention cases.

## 9. Failure scenario design

All 25 governed failure modes have a corresponding simulator scenario.

Each scenario defines:

- trigger mechanism
- progression duration
- affected signals
- signal direction/pattern
- production impact
- potential quality impact
- maintenance behavior
- recovery behavior

The resulting event chain remains traceable across domains.

## 10. Primary and secondary anomalies

Only one primary failure scenario is active on a machine at a time.

Secondary correlated anomalies are allowed.

Example:

```
Primary:
CNC-BRG

Secondary observations:
VIBRATION_HIGH
TEMPERATURE_HIGH
POWER_ABNORMAL
QUALITY_DEGRADATION
```

This preserves one primary ground-truth scenario while allowing realistic multi-signal observations.

## 11. Maintenance intervention

A scenario may terminate before failure when maintenance is initiated.

Example:

```
EARLY_DEGRADATION
      ↓
ML risk becomes high
      ↓
Predictive maintenance
      ↓
Repair
      ↓
RECOVERY
      ↓
RUNNING
```

This later supports analysis of:

- predicted failure
- actual failure
- avoided failure
- false positive
- maintenance response

## 12. Simulator lineage

Every generated event should retain:

```
simulator_run_id
scenario_id
scenario_instance_id
generated_at_utc
deterministic_seed
```

When one event causes another, correlation_id and causation_id should also be populated.

## 13. What the simulator must not do

Do not:

- generate every sensor independently
- generate a failure with no preceding health trajectory
- automatically turn every anomaly into a failure
- make every failure produce the same downtime duration
- make every repair perfectly successful
- use modelled defect probability as the actual defect label
- erase degradation history after repair
- generate impossible physical values
- hide stochastic behavior behind an unreproducible random seed

## Stage boundary

Stage 3.3 locks the simulation world and 25 scenario definitions.

The next stage is **Stage 3.4 — Simulator Data-Generation Contracts**, where we define the exact generated record shape and orchestration rules for bootstrap history, production orders, batches, scenario instances, event sequencing and replay/idempotency before Python implementation begins.
