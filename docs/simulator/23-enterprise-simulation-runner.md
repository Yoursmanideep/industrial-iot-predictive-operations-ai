# 23 — Enterprise Simulation Runner

Stage 3.8 turns the synchronized simulation engine into a repeatable enterprise run.

## Modes

BOOTSTRAP uses the governed historical machine-state distribution and baseline telemetry cadence.

BACKFILL uses the governed historical baseline cadence for a finite requested window.

LIVE uses the 5-second simulation cadence and 5-second telemetry cadence.

REPLAY requires the same deterministic run identity and seed to reproduce event identities; source-run artifact comparison is a later replay-validation layer.

## Run identity

When a run ID is supplied, it is used directly.

When it is omitted, a deterministic UUIDv5-style run ID is derived from mode, seed, simulation start and simulation end.

This makes repeated runs with the same inputs reproducible.

## Machine world

The runner loads the exact 270-machine governed master.

BOOTSTRAP additionally applies the configured initial distribution:

RUNNING 80%, IDLE 8%, SETUP 4%, MAINTENANCE 3%, OFFLINE 5%.

The state assignment is deterministic per machine and seed.

## Production scheduling

Orders are generated from the enterprise production generator.

Only plans whose planned start has been reached are registered into the active simulation world.

The runner can move to the next order boundary when necessary instead of registering an order late inside a coarse historical tick.

## Event streaming

Events are written incrementally, avoiding retention of the entire historical event population in memory.

Partitions use event type, event date and plant.

run_event_manifest.json records per-stream counts, event-time bounds and generation-sequence bounds.

simulation_run_manifest.json records run identity, mode, seed, simulation window, tick count, registered order count and total event count.

## CLI

The industrial-sim command supports mode, start/end timestamps, duration in minutes, seed, run ID, repository root and output directory.

Example:

industrial-sim --mode LIVE --start 2026-09-21T06:00:00Z --minutes 5 --output output/simulator

## Verification

Tests cover deterministic bootstrap machine state assignment, append-safe stream output, deterministic run identity and five-second live telemetry cadence.

Local pytest execution remains pending because the current environment does not have a working checkout of the GitHub repository for runtime execution.