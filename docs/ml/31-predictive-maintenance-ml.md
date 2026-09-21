# 31 — Predictive Maintenance ML Layer

## Scope

Stage 3.16 converts the deterministic Industrial IoT history into a governed supervised-learning path for machine failure-risk prediction.

Target:

Will this machine experience a causal MachineFaulted event within the next 60 minutes?

The target is tied to the simulator's actual causal operational event stream. Scenario metadata remains audit/label lineage and is excluded from the model feature vector.

## Architecture

Silver telemetry + operational events + production events + MDM
|
v
5-minute feature snapshots
|
+--- causal future-fault label
|
v
temporal train / validation / test
|
v
MLflow experiment
|
+--- Random Forest
+--- Extra Trees
|
v
selected sklearn model
|
+--- MLflow registry
+--- Fabric PREDICT batch scoring
+--- real-time endpoint via Dataflow Gen2
|
v
machine risk outputs
|
+--- Warehouse Gold
+--- Eventhouse
+--- Power BI / operations

## Feature engineering

The feature layer operates at a 5-minute machine snapshot grain so the same input contract can be reused for batch and real-time inference.

Current features cover temperature, vibration, pressure, power, cycle time, throughput, quality score, positioning error, motor current and torque.

Rolling features are calculated over 15-minute and 60-minute windows for the main diagnostic signals. Context features include alarm counts, 24-hour fault history, communication-loss count, line production/loss quantity, utilization proxy, shift, time-of-day encoding, machine age and machine type code.

Machine-type-specific signals stay nullable. The stable model vector therefore preserves the distinction between a signal that is measured and one that is not applicable.

## Causal label generation

Labels come from future MachineFaulted events for the same machine.

A feature row is positive when a MachineFaulted event occurs strictly after the feature timestamp and within the 60-minute horizon.

A row is a known negative only when enough forward history exists to prove that no fault occurred during the horizon. Rows inside the final 60 minutes of available history are right-censored and excluded from training.

Post-fault and maintenance-state rows are excluded from the training source.

The simulator's avoided predictive-maintenance scenarios are not converted into counterfactual failures. They remain observed no-fault outcomes for this first target.

## Leakage controls

The following attributes are excluded from the model vector:

- scenario_id
- scenario_instance_id
- failure_mode_code
- fault_code
- next_fault_event_id
- next_fault_time_utc
- label_failure_60m

Future operational events are used only to produce the target label. The model never receives future values as input.

## Training and validation

The training notebook uses a chronological split:

- 70 percent train
- 15 percent validation
- 15 percent test

The test period remains untouched until final champion evaluation.

Spark performs the feature-engineering workload. A deterministic bounded sample is used for sklearn training so the experiment remains controlled for notebook execution while retaining reproducible sampling.

Two endpoint-compatible sklearn tree regressors are compared:

- RandomForestRegressor
- ExtraTreesRegressor

They learn a continuous risk score from binary failure labels. Validation selection uses average precision, with ROC AUC as the tie-break metric.

An operating threshold is selected from the validation precision/recall curve against the configured minimum recall target.

No target performance is assumed. All reported performance is produced by the actual Fabric run.

## MLflow and model registry

Experiment:

ApexIndustrialIoT_PredictiveMaintenance

Registered model:

ApexIndustrialIoT_PredictiveMaintenance_FailureRisk

The training notebook logs parameters, metrics, tags, feature/label versions, the model signature and input example, then registers the selected model version.

Current Microsoft Fabric documentation states that Fabric supports MLflow up to 3.1 and that MLflow 3 adds first-class LoggedModel tracking. Fabric also uses an MLflow-backed model registry for versioned model management.

Reference: https://learn.microsoft.com/en-us/fabric/data-science/mlflow-3-overview

## Batch scoring

The batch scoring notebook uses the Fabric MLFlowTransformer / PREDICT pattern with an explicit registered model name and version.

Outputs are written to:

ml.machine_failure_prediction

The Warehouse durable surface is:

gold.fact_machine_failure_prediction

with:

mart.v_machine_failure_risk_latest

Reference: https://learn.microsoft.com/en-us/fabric/data-science/tutorial-data-science-batch-scoring

## Real-time inference

The real-time path is:

Eventhouse feature projection
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
+--- KQL
+--- Power BI
+--- future operational rules

The endpoint path is currently a Preview capability in Microsoft Fabric. The repository therefore keeps endpoint activation, permissions and connection binding as deployment-time concerns.

Dataflow Gen2 authenticates using a service principal whose secret is supplied through Fabric parameters or a variable library. No secret is stored in Git.

The current heuristic rt_machine_risk path remains as an explicit fallback and is never relabeled as an ML prediction.

References:
https://learn.microsoft.com/en-us/fabric/data-science/model-endpoints
https://learn.microsoft.com/en-us/fabric/data-factory/dataflow-gen2-machine-learning-model-endpoints

## Risk bands

Synthetic starting bands:

- LOW: below 0.35
- MEDIUM: 0.35 to below 0.60
- HIGH: 0.60 to below 0.80
- CRITICAL: 0.80 and above

These values are engineering defaults for routing and visualization, not validated production thresholds.

## Governance

Every prediction preserves feature version, model name/version, feature timestamp, scoring timestamp, prediction identity, inference mode and source run identity where available.

Only explicit registered model versions are eligible for scoring.

## Runtime boundary

Source-controlled artifacts are complete for Stage 3.16.

Actual runtime execution still requires populated Silver/MDM data, a Fabric MLflow experiment, a successful training run with positive failure examples, a registered model version, and an active endpoint plus Dataflow Gen2 binding for the real-time path.

No runtime training, registration or endpoint execution is claimed from Git alone.
