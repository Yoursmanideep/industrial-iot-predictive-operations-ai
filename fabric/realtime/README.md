# Real-Time Intelligence Layer

Stage 3.15 provides the hot operational path for Industrial IoT.
Stage 3.16 adds ML failure-risk enrichment without replacing the existing deterministic heuristic.

## Components

- Eventstream topology
- Eventhouse raw event table
- KQL real-time functions
- Activator trigger contract
- Power Automate incident workflows
- Real-Time Dashboard blueprint
- Dataverse operational entity contract
- ML feature and prediction contracts

## ML path

Eventhouse
|
v
5-minute machine feature projection
|
v
Dataflow Gen2
|
v
Fabric ML Model Endpoint
|
v
IndustrialIoTMLPrediction
|
+--- KQL / Power BI
+--- future operational rules

The real-time endpoint capability is currently documented by Microsoft as Preview. Endpoint activation and connection binding are deployment-time activities.

## KQL functions

Stage 3.15:

- rt_latest_machine_telemetry
- rt_recent_critical_incidents
- rt_machine_risk
- rt_production_15m
- rt_production_losses
- rt_plant_realtime_kpi
- rt_stream_health

Stage 3.16:

- rt_ml_latest_prediction
- rt_ml_high_risk_machines
- rt_ml_endpoint_health

## Design principle

Eventhouse is the hot analytical store. Warehouse Gold remains the durable historical KPI and ML prediction surface.

The existing rt_machine_risk query is a heuristic fallback. It is intentionally distinguished from the registered ML model.

## Deployment

The repository provides source-controlled contracts and code. Actual Eventstream, Eventhouse, Activator, Power Automate, Dataflow Gen2 and ML endpoint connection references are environment-specific and must be bound during deployment.
