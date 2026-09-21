# Microsoft Fabric Layer

Stage 3.10 introduced replay-safe validated ingestion into Bronze.
Stage 3.11 introduced curated Silver Delta processing.
Stage 3.12 introduced the SQL-first Warehouse Gold analytical model.
Stage 3.13 introduced the Power BI semantic model and Plant RLS.
Stage 3.14 introduced the PBIP/PBIR report project.
Stage 3.15 introduced the Eventstream/Eventhouse/Activator hot operational path.
Stage 3.16 introduces the predictive-maintenance ML lifecycle.
Stage 3.17 introduces ML monitoring, explainability and operational decision workflows.

Structure:

- ingestion/ — deterministic batch identity, checkpoints, scanning and replay-safe Bronze landing
- notebooks/ — Bronze, Silver and ML Spark notebooks
- sql/ — ingestion, Silver and Warehouse control models
- kql/ — Eventhouse destination schemas and real-time queries
- pipelines/ — deployment contracts
- dataflows/ — Power Query functions for ML endpoint enrichment
- silver/ — Silver-layer documentation and contract tests
- warehouse/ — Gold star schema, facts, OEE, KPI and ML prediction views
- ml/ — ML contract tests
- realtime/ — hot-path and ML endpoint contracts

ML outputs:

- ml.machine_failure_features
- ml.machine_failure_training
- ml.machine_failure_prediction
- ml.machine_failure_training_run
- gold.fact_machine_failure_prediction
- mart.v_machine_failure_risk_latest
- IndustrialIoTMLPrediction

Stage 3.16 stores model contracts, training code and deployment definitions in Git. Fabric stores the experiment runs and registered model versions in the workspace.
