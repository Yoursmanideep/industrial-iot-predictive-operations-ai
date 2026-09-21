# 27 — SQL-first Warehouse / Gold Layer

## Purpose

Stage 3.12 establishes the SQL-first analytical Warehouse between curated Silver data and the Power BI consumption layer.

Fabric Data Warehouse is designed for star/snowflake schemas, curated data marts, and governed BI semantic models. The Warehouse supports T-SQL tables, views, stored procedures and MERGE transformations, making it the SQL-first Gold surface for this project.

## Architecture

Silver Delta
    ↓
Warehouse staging
    ↓
Conformed dimensions
    ↓
Append-safe event facts
    ↓
Shift-split downtime intervals
    ↓
Machine/shift/business-date OEE
    ↓
mart views
    ↓
Power BI semantic model

## Conformed dimensions

The Warehouse reuses the stable MDM surrogate keys:

- date
- shift
- shift calendar
- plant
- production area
- line
- machine model
- machine
- product
- operator
- technician
- supplier
- spare part
- failure mode
- alarm code
- production reason
- quality defect

SCD2 effective dates are preserved for historized dimensions.

## Facts

gold.fact_machine_telemetry
gold.fact_machine_operational_event
gold.fact_downtime_interval
gold.fact_production_event
gold.fact_production_loss
gold.fact_maintenance_event
gold.fact_quality_event
gold.fact_oee_daily

Every event-driven fact keeps event identity, ingestion lineage and source payload hash where relevant.

## Shift calendar

The project uses Asia/Kolkata with the manufacturing business day beginning at 06:00 local time.

The Warehouse generates a physical shift calendar in UTC:

- SH1: 06:00–14:00 local
- SH2: 14:00–22:00 local
- SH3: 22:00–06:00 local next day

State intervals are split across shift boundaries so downtime seconds are allocated to the correct shift.

## OEE grain

The physical OEE fact is business date × shift × plant × line × machine where available.

For production events without a machine identifier, the machine key can remain the controlled unknown member while line and product context are retained.

## OEE definitions

Availability = Run Time / Planned Production Time

Performance = Ideal Production Seconds / Run Time

Quality = Good Quantity / Total Quantity

OEE = Availability × Performance × Quality

Planned production time is scheduled shift time minus planned stops.

Unplanned downtime is measured separately.

The machine-level fact stores component values. The mart.v_oee_daily view recalculates line-level results from summed time and quantity components rather than averaging percentages.

## Production

fact_production_event preserves:

- actual quantity
- good quantity
- rejected quantity
- production losses
- order/batch lineage
- product and machine/line context

fact_production_loss is a narrow analytical subset for loss-focused reporting.

## Downtime

fact_downtime_interval is derived from state-change events and uses the next state-change event as the interval boundary.

Downtime categories include planned maintenance, planned setup, planned idle, unplanned fault, unplanned offline, unplanned blocked, unplanned starved, unplanned maintenance, unplanned setup, and idle/no-demand.

Intervals can cross processing windows and are therefore updated by MERGE when a later window extends an existing interval segment.

## Maintenance and quality

The physical Gold fact tables are provisioned now:

fact_maintenance_event
fact_quality_event

Their staging contracts and Gold mappings are ready, but those facts remain empty until the corresponding Silver maintenance and quality domains are populated. Gold does not bypass the medallion layer to read raw Bronze directly.

## Power BI surface

Power BI is intended to consume the mart schema:

mart.v_oee_daily
mart.v_oee_by_machine
mart.v_production_daily
mart.v_downtime_daily
mart.v_machine_health_latest
mart.v_operational_incidents
mart.v_maintenance_summary
mart.v_quality_summary

This keeps KPI definitions in the Warehouse and leaves the semantic model responsible for relationships, business-friendly naming, model-level measures where appropriate, and report presentation.

## Deployment

The repository contains:

- Warehouse staging DDL
- Gold star-schema DDL
- dimension load procedures
- fact and OEE procedures
- KPI views
- orchestration procedure
- Silver-to-Gold pipeline contract
- contract tests

Actual Warehouse creation, Lakehouse-to-Warehouse connections and environment credentials remain deployment-time configuration.