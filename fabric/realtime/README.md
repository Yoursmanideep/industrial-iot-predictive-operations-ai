# Real-Time Intelligence Layer

Stage 3.15 provides the hot operational path for Industrial IoT.

## Components

- Eventstream topology
- Eventhouse raw event table
- KQL real-time functions
- Activator trigger contract
- Power Automate incident workflows
- Real-Time Dashboard blueprint
- Dataverse operational entity contract

## KQL functions

- `rt_latest_machine_telemetry`
- `rt_recent_critical_incidents`
- `rt_machine_risk`
- `rt_production_15m`
- `rt_production_losses`
- `rt_plant_realtime_kpi`
- `rt_stream_health`

## Alert flow

Eventstream → Activator → Power Automate → Dataverse / Teams / Email

## Design principle

Eventhouse is the hot analytical store. Warehouse Gold remains the durable historical KPI surface.

Activator handles near-real-time detection and action; it does not replace the historical data model.

## Deployment

The repository provides source-controlled contracts and templates. Actual Eventstream, Eventhouse, Activator and Power Automate connection references are environment-specific and must be bound during Fabric deployment.