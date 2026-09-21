# 29 — Power BI Report Implementation

## Scope

Stage 3.14 establishes the source-controlled Power BI report project on top of the Stage 3.13 semantic model.

## PBIP/PBIR structure

The project uses:

- ApexIndustrialIoT.pbip
- ApexIndustrialIoT.Report/definition.pbir
- ApexIndustrialIoT.Report/definition/
- ApexIndustrialIoT.SemanticModel/

PBIR stores report definition, page definitions and visual definitions as separate files. This is intended to make report changes easier to review and merge in Git.

## Report pages

The implementation contains seven pages:

1. Executive Overview
2. Plant Operations
3. Machine Health
4. Downtime & Reliability
5. Production & Quality
6. Machine Detail — hidden drill-through target
7. Machine Tooltip — hidden tooltip page

## Implemented visuals

The current PBIR definition contains card visuals for headline KPIs, bar charts for categorical comparisons, line charts for time trends and slicers for date/plant/shift filtering.

The primary pages use a 1280 × 720 canvas.

Visual IDs use 20-character lowercase hexadecimal identifiers.

## Drill-through

Machine Detail is a hidden page bound to Machine.machine_id.

The page includes the drill-through filter metadata and the matching page-binding parameter required for a PBIR drill-through target.

## Tooltip

Machine Tooltip is hidden from normal navigation and is defined as a Tooltip page.

It contains the machine OEE, temperature and vibration context.

## Interactions

report_interactions.yaml defines:

- report navigation
- machine drill-through
- machine tooltip
- bookmark intentions
- RLS preservation

The bookmark contract is kept source-controlled as business interaction metadata; final interactive bookmark state can be refined in Power BI Desktop/Fabric authoring.

## Report design

The report keeps the existing OEE definitions from the semantic model:

Availability %, Performance %, Quality %, OEE % and production/downtime measures.

No visual is intended to average percentage KPIs across machines. Aggregations use the semantic model measures.

## Runtime boundary

The repository contains the PBIP/PBIR project definition and source-controlled report structure.

Actual rendering validation, visual rendering behavior, semantic-model binding and publication require a Power BI Desktop/Fabric environment with the target Warehouse and semantic model available.

The available environment here does not provide that runtime bridge, so no claim of successful Desktop/Fabric publication is made.