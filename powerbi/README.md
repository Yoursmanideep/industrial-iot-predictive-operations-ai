# Power BI Semantic Model

Stage 3.13 adds a source-controlled TMDL semantic model for the Industrial IoT platform.

## Model

`ApexIndustrialIoT.SemanticModel`

Storage mode: Direct Lake on OneLake.

The model targets the physical Gold tables in the Fabric Warehouse. The OneLake connection expression contains deployment placeholders for workspace and Warehouse IDs; these must be replaced during environment deployment.

## Main dimensions

- Date
- Shift
- Plant
- Line
- Machine
- Product

## Main facts

- OEE
- Production
- Downtime
- Telemetry
- OperationalEvent

## Security

`Plant RLS` is a dynamic semantic-model role using `USERPRINCIPALNAME()` against the `PlantAccess` security mapping.

## Design rules

- single-direction relationships
- integer surrogate keys
- hidden fact foreign keys
- no direct dependency on Warehouse views for Direct Lake tables
- KPI measures use additive components rather than averaging percentages
- source lineage remains available in Gold facts

Power BI semantic-model definitions are kept in TMDL because the format is text-based and designed for source control/co-development. The current Fabric API also supports semantic-model definitions in TMDL format.

Actual Fabric semantic-model item creation and environment-specific connection binding remain deployment-time operations.