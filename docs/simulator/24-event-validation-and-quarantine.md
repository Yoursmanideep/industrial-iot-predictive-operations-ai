# 24 — Event Validation and Quarantine

Stage 3.9 adds the data-quality boundary between simulator generation and durable event output.

## Validation layers

Every generated event is evaluated in order by:

1. JSON Schema validation against the governed telemetry, operational or production contract.
2. Run lineage checks including simulator_run_id, event_id uniqueness and generation sequence.
3. Temporal checks including canonical UTC event time, ingestion time and bounded ingestion delay.
4. Causation checks requiring referenced parent events to already be accepted.
5. Correlation checks requiring child correlation to match its direct causal parent.
6. Scenario-lineage checks.
7. Production quantity and state-transition business rules.

## Invalid-event behavior

Invalid events are not repaired or silently discarded.

They are written to a quarantine partition containing:

- deterministic quarantine ID
- deterministic event-time reference
- reason codes
- detailed validation errors
- event identity and run identity
- complete original payload

Quarantine records are partitioned by event date and event type.

## Sequence behavior

Validation tracks both the last observed generation sequence and the last accepted generation sequence.

This prevents one quarantined record from causing artificial sequence-gap failures for every later valid event.

Causation still requires the parent to have been accepted.

## Durable output boundary

ValidatedEventStreamWriter is the runner-facing adapter.

Valid events flow into the normal telemetry, operational and production JSONL partitions.

Invalid events flow into quarantine instead.

The validation manifest reports valid count, quarantine count and total count.

The simulation run manifest also records these values.

## Determinism

Quarantine metadata is derived from the source event rather than wall-clock execution time.

UTC is enforced for event_time and ingestion_time.

## Verification

Tests cover valid acceptance, schema rejection, non-cascading sequence handling, missing causation, production quantity invariants, deterministic quarantine metadata and end-to-end valid/quarantine routing.

Runtime pytest execution remains pending because the current environment cannot clone the GitHub repository over the public network.