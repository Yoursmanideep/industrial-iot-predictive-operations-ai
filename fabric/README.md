# Microsoft Fabric Layer

Stage 3.10 introduced replay-safe validated ingestion into Bronze.
Stage 3.11 introduced curated Silver Delta processing.
Stage 3.12 introduces the SQL-first Warehouse Gold analytical model.

Structure:

- ingestion/ — deterministic batch identity, checkpoints, scanning and replay-safe Bronze landing
- notebooks/ — Bronze and Silver Spark transformations
- sql/ — ingestion, Silver and Warehouse control models
- kql/ — Eventhouse destination schema
- pipelines/ — deployment contracts
- silver/ — Silver-layer documentation and contract tests
- warehouse/ — staging contracts, Gold star schema, load procedures, OEE and KPI views

Gold outputs:

- gold dimensions for date, shift, plant, area, line, machine, product, people, parts and governed reference codes
- gold.fact_machine_telemetry
- gold.fact_machine_operational_event
- gold.fact_downtime_interval
- gold.fact_production_event
- gold.fact_production_loss
- gold.fact_maintenance_event
- gold.fact_quality_event
- gold.fact_oee_daily
- mart KPI and consumption views

Next layer: Power BI semantic model and enterprise reporting.
Stage 3.13 adds the source-controlled Power BI semantic model, Direct Lake TMDL definition, KPI measures and Plant RLS.

Stage 3.14 adds the PBIP/PBIR Power BI report project, operational pages, drill-through, tooltip, KPI visuals and report interaction contract.
