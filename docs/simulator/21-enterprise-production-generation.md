# 21 — Enterprise-Scale Deterministic Production Generation

Stage 3.6.1 scales production planning from individual order execution to deterministic enterprise generation.

## Scope

- 3 plants
- 15 production lines
- 12 seeded products
- 30–60 production orders per plant per business day
- 100–2,500 planned units per order
- 1–8 batches per order

## Deterministic planning

Each business day is seeded from simulator seed, plant ID and business date.

Product selection is deterministic and weighted by product family.

Line assignment is restricted to the owning plant's five lines and selects the earliest available compatible line.

Production order identity is derived from simulator run ID, plant, line, planned start and production sequence.

Planning itself has no event-generation side effects. The order event is created exactly once during instantiation.

## Time handling

Daily planning is anchored to the Asia/Kolkata 06:00 business shift boundary.

Generated timestamps are persisted as timezone-aware UTC timestamps.

Multiple batches on one order are sequenced by expected batch execution duration.

## Event batching

Production events are sorted by event_time, generation_sequence and event_id.

JSONL output is partitioned by:

event_date=YYYY-MM-DD/plant_id=PLT-XXX-01/production_events.jsonl

A production_event_manifest.json file records event count, partition count, first and last event time and generated partition files.

## Idempotency

Repeating the same generation run with the same simulator run ID, seed and configuration reproduces the same production order plan and deterministic identities.

A different simulator run ID produces a different identity namespace.

## Lifecycle events

Enterprise generation emits:

ProductionOrderCreated → ProductionOrderReleased → ProductionStarted → BatchStarted

Actual UnitProduced, loss, quality and maintenance events remain execution-stage outputs and are generated when the time-stepped machine/line simulation advances.

## Verification

Tests cover enterprise daily volume, plant-scoped line assignment, business-time anchoring, deterministic plan reproduction and partitioned event output with manifest creation.

Local pytest execution remains pending because the current execution environment has not been able to resolve the repository's GitHub DNS path.