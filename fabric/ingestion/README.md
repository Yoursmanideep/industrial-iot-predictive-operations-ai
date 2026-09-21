# Fabric Ingestion Adapter

This package is the ingestion control plane between validated simulator output and the Microsoft Fabric Bronze/Eventhouse layer.

## Design

Validated JSONL partition

→ deterministic batch manifest

→ deterministic idempotency key

→ checkpoint lookup

→ Bronze landing plan

→ Eventhouse routing metadata

## Idempotency

Business event identity remains event_id.

Batch identity is a SHA-256-derived IBT identifier based on run, source partition, file hash and sequence metadata.

Replay of the same source partition therefore resolves to the same ingestion batch identity.

At the event layer, a duplicate event_id is skipped. A duplicate event_id with conflicting payload hash is treated as a data-integrity conflict and should be quarantined.

## Checkpoint semantics

PLANNED → LOADING → COMPLETED is the normal state machine.

FAILED is retryable.

SKIPPED_DUPLICATE means the exact source batch was already successfully committed.

QUARANTINED means the source batch or event set failed a required integrity check and must not be promoted into Bronze as trusted data.

## Fabric destinations

Bronze landing uses the configured OneLake/Lakehouse Files root and preserves the source partition keys:

event_type / event_date / plant_id

Eventhouse routing is declared separately for telemetry, operational and production streams.

Workspace, Lakehouse and Eventhouse names are environment configuration, never Git-tracked credentials or secrets.

## SQL control plane

fabric/sql/001_ingestion_control.sql creates the control tables used for batch checkpoints and event-level idempotency.

The actual Fabric pipeline or notebook can use these tables as its transactional control plane while the source files remain immutable.

## Operational rule

Do not mark a batch COMPLETED until Bronze write success and event-level deduplication have both succeeded.

Do not delete source files as part of ingestion.

## Current scope

The repository provides deterministic planning, checkpoint and deduplication contracts. Fabric resource deployment and credential binding remain environment-specific deployment steps.