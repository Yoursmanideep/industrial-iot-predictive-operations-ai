# 22 — Synchronized Simulation Clock

Stage 3.7 introduces the authoritative time-stepped coordinator for machine telemetry, scenario progression, machine state and production execution.

## Tick contract

The default live simulation tick is 5 seconds.

At each tick:

1. Simulation time advances.
2. Active scenarios progress.
3. Scenario state changes emit operational events.
4. Machine state is reconciled with the scenario stage.
5. Environment, shift and workload context are evaluated.
6. Type-specific telemetry is generated.
7. Production accumulates elapsed execution time.
8. Every 30 seconds the active production batch executes against the current route-machine capacities.
9. Production losses can reference the MachineFaulted event that caused line unavailability.
10. Terminal scenario state is cleaned up after telemetry and production have consumed the current tick.

## Shared physical context

The same machine object and current simulation timestamp drive machine state, ambient conditions, workload, telemetry physics, scenario telemetry effects and production capacity.

This prevents telemetry, state and production from becoming separate synthetic timelines.

## Scenario causality

A scenario that reaches ANOMALY can emit AlarmRaised.

A scenario that reaches FAILURE can emit MachineFaulted followed by StateChanged, and the machine enters FAULT.

The failure state is visible to the same tick's telemetry and production execution.

When production reaches its aggregation boundary while a required route machine is FAULT, the line becomes unavailable and ProductionLossRecorded can reference the MachineFaulted event.

## Production cadence

The simulation clock remains 5 seconds for live operation.

Production output is aggregated over 30 seconds, matching the Stage 3.4 generation contract. This allows machine and scenario dynamics to evolve at higher resolution without creating one UnitProduced event every five seconds.

## Enterprise runtime world

The machine world loader hydrates all 270 governed machines from the master seed.

The integrated engine can then register production plans and activate deterministic scenarios against the same runtime machines.

## Determinism

Event IDs use the existing UUIDv5-style run namespace and generation sequence.

The synchronized engine preserves run lineage, deterministic event identity, deterministic scenario identity, monotonic generation sequence and canonical UTC event time.

## Verification

Integration tests cover the exact 270-machine world, normal 30-second production output, scenario ANOMALY to FAILURE, MachineFaulted and StateChanged generation, scenario-aware telemetry, production downtime after machine failure, machine-fault linkage to production loss and run-scoped sequence uniqueness.

Local pytest execution remains pending because the repository test environment is not available in the current execution session.