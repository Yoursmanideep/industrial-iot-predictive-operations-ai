# 33 — Stage 3.17 Verification

## Source-controlled scope

Stage 3.17 is complete at the repository-contract level.

Verified artifact groups:

- monitoring configuration
- monitoring and explainability notebook
- Warehouse monitoring, drift and explanation surfaces
- operationalization pipeline contract
- predictive-maintenance Activator rules
- Power Automate maintenance-review workflow
- Power Automate model-health workflow
- Power BI Direct Lake ML tables and report-page blueprint
- Dataverse model-risk and maintenance-review fields

## Runtime boundary

The repository does not claim live metric values, drift findings, model explanations, Activator executions or Power Automate runs.

Those values are created only after the corresponding Fabric items are deployed and executed against populated data.

## Governance controls

- no automatic machine stop from an ML prediction
- no automatic model promotion on a monitoring breach
- no automatic retraining from a monitoring breach
- prediction and model versions remain traceable
- feature version remains traceable
- Plant RLS applies to plant-scoped prediction data

## Current Microsoft Fabric references

ML experiment/model monitoring is documented by Microsoft as Preview.

ML model endpoints are documented as Preview.

Activator can trigger Power Automate workflows, and current Activator documentation also describes Warehouse SQL query monitoring as Preview.

References:
https://learn.microsoft.com/en-us/fabric/data-science/monitor-machine-learning-experiments-models
https://learn.microsoft.com/en-us/fabric/data-science/model-endpoints
https://learn.microsoft.com/en-us/fabric/real-time-intelligence/data-activator/activator-create-activators
