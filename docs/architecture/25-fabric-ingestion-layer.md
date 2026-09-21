# 25 — Fabric Ingestion Layer

Stage 3.10 establishes the boundary between validated simulator output and Microsoft Fabric ingestion.

## Flow

Validated simulator JSONL

→ logical source partition

→ deterministic ingestion batch ID

→ replay-safe checkpoint

→ immutable OneLake Files Bronze landing

→ Spark Delta upsert

→ Eventhouse routing metadata

## Fabric storage pattern

Raw source batches are kept in the Lakehouse Files area as the immutable landing layer.

Fabric Lakehouses use Delta Lake as the default table format for tables, and Spark can load JSON files from the Files area into Delta tables. The implementation therefore separates immutable raw landing from the queryable Bronze Delta table.

## Idempotency

Batch identity uses SHA-256 over the simulator run, logical source partition, source file hash, sequence range and event count.

Event identity remains event_id.

A replay of the exact source batch is skipped at batch level.

At event level, equal payload hash is a duplicate and a different payload hash for the same event_id is a conflict.

## Control plane

fabric/sql/001_ingestion_control.sql defines batch checkpoint and event log tables.

The Spark notebook uses Delta MERGE behavior for event and checkpoint upsert semantics.

## Eventhouse

The KQL schema declares separate destinations for MachineTelemetry, MachineOperationalEvent and ProductionEvent.

Fabric Eventstream can route real-time data to Eventhouse or Lakehouse destinations; this repository keeps the real-time routing contract separate from durable Bronze storage.

## Security

Workspace IDs, resource names and credentials are environment configuration.

No tokens, connection strings or secrets are committed.

## Deployment boundary

The repository contains the code, schemas, SQL control plane, KQL schema and pipeline contract.

Actual Fabric workspace deployment and managed identity/connection binding remain environment-specific.