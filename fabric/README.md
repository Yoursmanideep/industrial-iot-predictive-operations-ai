# Microsoft Fabric Layer

Stage 3.10 introduces the Fabric ingestion control plane.

Structure:

- ingestion/ — deterministic batch identity, checkpoints, scanning, planning and replay-safe Bronze landing
- notebooks/ — Fabric Spark Bronze Delta ingestion
- sql/ — ingestion control tables
- kql/ — Eventhouse destination schema
- pipelines/ — deployment contract for validated-to-Bronze flow

All Fabric resource names and credentials are externalized.

Next layer: curated Silver data engineering and SQL-first Warehouse modeling.