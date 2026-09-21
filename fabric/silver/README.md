# Fabric Silver Layer

Stage 3.11 converts validated Bronze events into curated Silver Delta tables.

Tables:

- `silver.machine_telemetry` — normalized machine measurements and simulator lineage
- `silver.machine_operational_event` — normalized state/alarm/fault/recovery events
- `silver.production_event` — normalized production order/batch/loss events
- `silver.rejected_event` — failed Silver quality/master-data checks with original payload
- `control.silver_load_audit` — run-level quality and processing metrics

Quality gates include event identity conflicts, required keys, timestamp validity, master-reference existence, machine/line consistency and production quantity accounting.

Late arrival handling is event-time based. Events older than the observed batch event-time frontier by the configured threshold are flagged rather than re-timestamped.

Silver is stored as Delta and keeps source lineage (`event_id`, `ingestion_batch_id`, `simulator_run_id`, `generation_sequence`) for traceability.