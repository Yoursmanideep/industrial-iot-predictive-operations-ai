# Microsoft Fabric Layer

Stage 3.10 introduced replay-safe validated ingestion into Bronze.

Stage 3.11 introduces curated Silver Delta processing.

Structure:

- `ingestion/` — deterministic batch identity, checkpoints, scanning and replay-safe Bronze landing
- `notebooks/` — Bronze and Silver Spark transformations
- `sql/` — ingestion and Silver control models
- `kql/` — Eventhouse destination schema
- `pipelines/` — deployment contracts
- `silver/` — Silver-layer documentation and contract tests

Silver outputs:

- `silver.machine_telemetry`
- `silver.machine_operational_event`
- `silver.production_event`
- `silver.rejected_event`
- `control.silver_load_audit`

Next layer: SQL-first Warehouse/Gold modeling and analytical fact/dimension design.