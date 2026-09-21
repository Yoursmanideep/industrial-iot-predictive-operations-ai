# 28 — Power BI Semantic Model and Security

## Purpose

Stage 3.13 establishes a source-controlled Power BI semantic model over the Warehouse Gold star schema.

## Semantic model format

The repository uses the TMDL semantic-model definition structure:

powerbi/ApexIndustrialIoT.SemanticModel/
  definition.pbism
  definition/
    database.tmdl
    model.tmdl
    expressions.tmdl
    relationships.tmdl
    cultures/
    roles/
    tables/

Microsoft documents TMDL as a text-based semantic-model format suitable for source control and co-development. Fabric semantic-model definitions can be stored using TMDL, and Power BI Projects use the same definition structure.

## Storage mode

The model is designed as Direct Lake on OneLake.

Direct Lake entity partitions point at physical Gold tables rather than SQL views. This keeps the core analytical tables compatible with the Direct Lake storage path and avoids making the main model dependent on view-based fallback behavior.

The OneLake connection expression contains deployment placeholders:

https://onelake.dfs.fabric.microsoft.com/<FABRIC_WORKSPACE_ID>/<FABRIC_WAREHOUSE_ID>

These values are environment-specific and are not committed as tenant-specific infrastructure configuration.

## Model tables

Dimensions:

- Date
- Shift
- Plant
- Line
- Machine
- Product

Facts:

- OEE
- Production
- Downtime
- Telemetry
- OperationalEvent

Security:

- PlantAccess

## Relationship design

Fact tables filter through conformed dimensions using single-direction relationships.

The model avoids bidirectional relationships and many-to-many relationships in the core star schema.

Fact foreign keys are hidden from report authors.

## Measures

The model defines core operational measures:

- Availability %
- Performance %
- Quality %
- OEE %
- OEE YTD %
- OEE % Change vs Prior Day
- Good Units
- Rejected Units
- Production Yield %
- Downtime Minutes
- Unplanned Downtime Minutes
- Fault Downtime Minutes
- Alarm Count
- Fault Count
- Communication Loss Count

Percentage measures are returned as decimals and formatted as percentages.

## RLS

The `Plant RLS` role evaluates `USERPRINCIPALNAME()` against `PlantAccess[user_principal_name]` and filters the Plant dimension.

Because the Plant dimension is on the one-side of the star relationships, the Plant filter propagates to the related facts.

Production and maintenance identities are represented by placeholder `.example` principals in the security seed SQL only; production user/group assignments must be configured outside Git.

## Security boundary

Model-level RLS protects report consumption through the semantic model.

Microsoft's current OneLake security guidance also supports RLS/CLS at the OneLake layer, including Direct Lake on OneLake. This repository keeps the model role explicit while leaving cross-engine OneLake authorization as a deployment/security-governance step.

## Report blueprint

report_blueprint.yaml defines five planned operational pages:

1. Executive Overview
2. Plant Operations
3. Machine Health
4. Downtime & Reliability
5. Production & Quality

The blueprint defines the business questions and measures without pretending that a published PBIR report already exists.

## Deployment

The semantic model definition is source-controlled.

Workspace binding, Warehouse ID, semantic-model item creation, credential/cloud-connection configuration and RLS role assignments are deployment-time operations.