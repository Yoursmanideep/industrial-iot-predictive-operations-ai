# 32 — ML Operationalization

## Scope

Stage 3.17 turns the Stage 3.16 predictive-maintenance model into an operationally governed decision-support capability.

The layer adds:

- model performance monitoring
- feature drift monitoring
- model feature-importance explanations
- predictive-maintenance Activator rules
- Power Automate maintenance-review workflow
- Warehouse monitoring and explanation marts
- Power BI predictive-maintenance reporting blueprint

## Monitoring

The monitoring notebook evaluates a recent scoring window against explicit thresholds.

Tracked metrics include:

- prediction coverage
- critical-risk rate
- ROC AUC when forward labels are available
- average precision when forward labels are available
- Brier score when forward labels are available
- PSI for selected feature distributions

A monitoring breach creates a review state. The design does not automatically promote a model or retrain it from a breach.

## Explainability

The registered sklearn model's feature_importances_ values are persisted with model version and feature version.

The explanation surface is decision support for engineers. It does not establish causality and it is not used to automatically stop equipment.

Microsoft Fabric also provides a TabularSHAP explainer path for tabular models; this repository keeps the current implementation dependency-light and versioned around the model's native sklearn feature importance, while leaving SHAP as an extensibility point.

Reference: https://learn.microsoft.com/en-us/fabric/data-science/tabular-shap-explainer

## Operational integration

High and critical model-risk predictions are routed to an Activator contract that creates a predictive-maintenance review work item through Power Automate.

The workflow:

ML prediction
→ Activator
→ Power Automate
→ Dataverse MaintenanceWorkItem
→ Reliability Engineering + Plant Operations

The workflow never commands an automatic machine stop.

Model-monitoring breaches use a separate health-review action so model degradation is handled differently from equipment-risk events.

Fabric Activator supports rules on event data and can trigger Power Automate workflows; it also supports KQL-driven conditions and Fabric item actions.

References:
https://learn.microsoft.com/en-us/fabric/real-time-intelligence/data-activator/activator-trigger-model
https://learn.microsoft.com/en-us/fabric/real-time-intelligence/data-activator/activator-create-activators

## Power BI

The Predictive Maintenance report page combines:

- actionable machine risk
- risk history
- top feature importance
- model health
- drift exceptions

The page remains subject to the same Plant RLS because prediction and monitoring data are part of the plant-scoped operational model.

## Runtime boundary

Actual model monitoring values, drift statistics, explanations and Activator executions are generated only after the Fabric notebooks and deployed items run against populated data.

No production model-health result is claimed from Git artifacts alone.
