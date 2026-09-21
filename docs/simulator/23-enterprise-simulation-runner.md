# 23 — Enterprise Simulation Runner

Stage 3.8 turns the synchronized simulation engine into a repeatable enterprise run.

## Modes

BOOTSTRAP uses the governed historical machine-state distribution and baseline telemetry cadence.

BACKFILL uses the governed historical baseline cadence for a finite requested window.

LIVE uses the 5-second simulation cadence.

REPLAY reuses the supplied simulator run identity and seed so deterministic event semantics can be reproduced.

## Run identity

When a run ID is supplied, it is used directly.

When it is omitted, a deterministic UUIDv5-style run ID is derived from mode, seed, simulation start and simulation end.

This makes repeated CLI or API runs with the same inputs reproducible.

## Machine world

The runner loads the exact 270-machine governed master.

BOOTSTRAP additionally applies the configured initial distribution:

RUNNING 80%, IDLE 8%, SETUP 4%, MAINTENANCE 3%, OFFLINE 5%.

The state assignment is deterministic per machine and seed.

## Production scheduling

Orders are generated from the enterprise production generator.

Only plans whose planned start has been reached are registered into the active simulation world.

The runner moves to the next order boundary when necessary instead of registering an order late inside a coarse historical tick.

## Event streaming

Events are written incrementally so a long historical run does not require retaining the complete event history in memory.

Partitions use:

event_type=<telemetry|operational|production>/event_date=YYYY-MM-DD/plant_id=<plant>/...

The writer maintains run-scoped generation-sequence monotonicity independently for each event stream.

Two manifests are produced:

run_event_manifest.json — per-stream counts, event-time bounds and sequence bounds.

simulation_run_manifest.json — run identity, mode, seed, simulation window, tick count, registered order count and total event count.

## CLI

The industrial-sim command now supports mode, start/end timestamps, duration in minutes, seed, run ID, repository root and output directory.

Example execution shape:

industrial-sim --mode LIVE --start 2026-09-21T06:00:00Z --minutes 5 --output output/simulator

## Verification

Stage tests cover deterministic bootstrap machine states, writer append behavior and deterministic default run identity.

Integration coverage from Stage 3.7 remains the authoritative test of synchronized machine, scenario, telemetry and production behavior.

Runtime pytest execution remains pending because this environment cannot execute the repository test suite against the GitHub workspace.