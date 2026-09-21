# 13 — Python Simulator Architecture

## Stage
3.5.1 — Foundation and deterministic run engine

## Architecture goal
The simulator is designed as a stateful Python application with explicit domain boundaries. Generation logic is separated from orchestration so later stages can add realistic machine behavior without rewriting run management.

## Package boundaries

simulator/src/industrial_sim/

- config — typed configuration loading and validation
- domain — core business/domain objects such as SimulationRun
- engine — simulation clock, run context and orchestration
- lineage — deterministic identity and simulator trace utilities
- machines — reserved for machine models and machine state behavior
- scenarios — reserved for degradation/failure scenario execution
- production — reserved for orders, batches and production execution
- quality — reserved for inspections, measurements and defect outcomes
- maintenance — reserved for work-order and maintenance lifecycle behavior
- events — reserved for event envelopes and event builders
- telemetry — reserved for machine-type telemetry generation
- validation — reserved for schema and invariant validation
- cli — command-line entry points

## Foundation sequence

1. Load Stage 3.4 generation contract.
2. Create a SimulationRun.
3. Create SimulationContext and SimulationClock.
4. Advance simulation time deterministically.
5. Reserve generation_sequence as the run-scoped event ordering mechanism.
6. Generate deterministic identifiers from stable inputs.

## Determinism rules

- Simulation time never depends on wall-clock elapsed time.
- Randomness will use seeded, stable streams per logical entity or scenario rather than a single uncontrolled global stream.
- Identifier generation will use stable UUIDv5 derivation where the data contract requires reproducibility.
- Configuration and generator versions are carried by run context.

## Dependency direction

CLI → engine → domain/config/lineage

Later domain behavior modules will depend on core domain types and configuration, while the core run engine will not depend on machine-specific implementations.

## Stage 3.5.1 non-goals

- no machine physics
- no scenario progression implementation
- no production-rate model
- no quality defect model
- no maintenance workflow execution
- no streaming sink
- no Fabric connector

Those components are deliberately deferred until the foundation is verified.

## Verification criteria

- Python package metadata is present.
- package initialization exists for core namespaces.
- generation contract loader validates required fields.
- SimulationRun enforces time ordering and replay requirements.
- SimulationClock rejects invalid backwards movement.
- deterministic event identity is stable for the same inputs.
- run engine uses the configured tick size and default seed.
- pytest coverage exists for identity, clock and run-engine foundations.

## Next stage
3.5.2 — Machine state model and machine-type behavior interfaces.