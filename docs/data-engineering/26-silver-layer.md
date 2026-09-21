# 26 — Bronze to Silver Data Engineering

## Purpose

Stage 3.11 converts the validated Bronze event store into reusable Silver Delta tables.

Microsoft's current Fabric guidance describes medallion architecture as Bronze/raw, Silver/enriched and Gold/curated. The Silver layer is where data is cleansed, standardized and deduplicated, and Silver/Gold are typically stored as Delta tables. citeturn957561search0turn957561search4

## Silver outputs

```text
silver.machine_telemetry
silver.machine_operational_event
silver.production_event
silver.rejected_event
control.silver_load_audit
```

## Processing stages

```text
Bronze Delta
   ↓
event-time normalization to UTC
   ↓
event_id conflict detection
   ↓
duplicate elimination
   ↓
batch-scoped late-arrival flag
   ↓
event-time SCD2 master lookup
   ↓
hierarchy and quantity validation
   ↓
domain projection
   ↓
Silver Delta
```

## Duplicate policy

One business event is identified by immutable `event_id`.

If the same event ID occurs with the same payload hash, only one record is retained in Silver.

If the same event ID has different payload hashes, all conflicting occurrences are rejected and the original payload remains available through Bronze.

## Late arrival policy

Silver does not change `event_time`.

An event is flagged as late when its `event_time` falls more than the configured threshold behind the maximum event time observed within its ingestion batch.

This avoids incorrectly labeling an entire historical rebuild as late.

## Master-data validation

Machine, line, plant and product references are resolved using the event date against SCD2 effective dates where applicable.

Events failing the master-data gate are written to `silver.rejected_event` with the original payload and rejection code.

## Production accounting

The Silver quality gate preserves the production invariant:

`good_quantity + rejected_quantity <= actual_quantity`.

Negative production quantities are rejected.

## Audit

Every Silver run records source rows, duplicate rows, conflicting event IDs, accepted rows, rejected rows, late arrivals and master-reference failures in `control.silver_load_audit`.

## Deployment

The repository provides the Spark transformation notebook, Delta-oriented table contract, SQL control/rejection model, pipeline contract and local contract tests.

Actual Fabric workspace binding remains environment-specific.