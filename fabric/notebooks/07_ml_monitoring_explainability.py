# Fabric Spark notebook: predictive-maintenance model monitoring and explainability
#
# Produces operational monitoring metrics, feature-drift measurements and
# model feature-importance explanations. Monitoring does not auto-promote or
# auto-retrain a model.

from datetime import datetime, timedelta, timezone
import math

import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
import yaml

from pyspark.sql import functions as F


CONFIG_PATH = "../config/ml_operational_monitoring.yaml"
ML_CONFIG_PATH = "../config/predictive_maintenance_ml.yaml"

FEATURE_TABLE = "ml.machine_failure_features"
TRAINING_TABLE = "ml.machine_failure_training"
PREDICTION_TABLE = "ml.machine_failure_prediction"
TRAINING_AUDIT_TABLE = "ml.machine_failure_training_run"
MONITORING_TABLE = "ml.machine_failure_model_monitoring"
DRIFT_TABLE = "ml.machine_failure_feature_drift"
EXPLANATION_TABLE = "ml.machine_failure_feature_explanation"

with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
    MONITOR_CFG = yaml.safe_load(handle)
with open(ML_CONFIG_PATH, "r", encoding="utf-8") as handle:
    ML_CFG = yaml.safe_load(handle)

MODEL_NAME = MONITOR_CFG["monitoring"]["model_name"]
FEATURE_VERSION = ML_CFG["feature_engineering"]["feature_version"]

DRIFT_FEATURES = MONITOR_CFG["monitoring"]["drift_features"]
THRESHOLDS = MONITOR_CFG["monitoring"]["thresholds"]
RECENT_DAYS = int(MONITOR_CFG["monitoring"]["recent_window_days"])
BASELINE_DAYS = int(MONITOR_CFG["monitoring"]["baseline_window_days"])
TOP_K = int(MONITOR_CFG["explainability"]["top_k"])

MODEL_FEATURES = [
    "machine_type_code", "shift_code", "hour_sin", "hour_cos",
    "temperature_c", "vibration_mm_s", "pressure_bar", "power_kw",
    "cycle_time_s", "throughput_unit_min", "quality_score_pct",
    "position_error_mm", "motor_current_a", "torque_nm",
    "temperature_c_mean_15m", "temperature_c_std_15m", "temperature_c_delta_15m",
    "temperature_c_mean_60m", "temperature_c_std_60m", "temperature_c_delta_60m",
    "vibration_mm_s_mean_15m", "vibration_mm_s_std_15m", "vibration_mm_s_delta_15m",
    "vibration_mm_s_mean_60m", "vibration_mm_s_std_60m", "vibration_mm_s_delta_60m",
    "pressure_bar_mean_15m", "pressure_bar_std_15m", "pressure_bar_delta_15m",
    "pressure_bar_mean_60m", "pressure_bar_std_60m", "pressure_bar_delta_60m",
    "power_kw_mean_15m", "power_kw_std_15m", "power_kw_delta_15m",
    "power_kw_mean_60m", "power_kw_std_60m", "power_kw_delta_60m",
    "machine_age_days",
    "alarm_count_15m", "alarm_count_60m", "fault_count_24h",
    "communication_loss_count_60m",
    "line_actual_quantity_15m", "line_loss_quantity_15m",
    "line_actual_quantity_60m", "line_loss_quantity_60m",
    "utilization_proxy_15m",
]

NUMERIC_FEATURES = [
    "temperature_c", "vibration_mm_s", "pressure_bar", "power_kw",
    "cycle_time_s", "throughput_unit_min", "quality_score_pct",
    "position_error_mm", "motor_current_a", "torque_nm",
    "alarm_count_15m", "utilization_proxy_15m",
]


def psi(expected, actual, bins=10):
    expected = pd.Series(expected).dropna().astype(float)
    actual = pd.Series(actual).dropna().astype(float)
    if expected.empty or actual.empty:
        return float("nan")
    edges = np.unique(np.quantile(expected, np.linspace(0.0, 1.0, bins + 1)))
    if len(edges) < 3:
        return 0.0
    edges[0] = -np.inf
    edges[-1] = np.inf
    expected_counts = np.histogram(expected, bins=edges)[0].astype(float)
    actual_counts = np.histogram(actual, bins=edges)[0].astype(float)
    expected_pct = np.maximum(expected_counts / expected_counts.sum(), 1e-6)
    actual_pct = np.maximum(actual_counts / actual_counts.sum(), 1e-6)
    return float(np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct)))


def status_from_threshold(value, threshold, direction):
    if math.isnan(value):
        return "UNKNOWN"
    if direction == "min":
        return "PASS" if value >= threshold else "BREACH"
    return "PASS" if value <= threshold else "BREACH"


def append_monitoring(rows):
    if not rows:
        return
    spark.createDataFrame(rows).withColumn(
        "created_at_utc", F.current_timestamp()
    ).write.format("delta").mode("append").saveAsTable(MONITORING_TABLE)


def ensure_output_tables():
    spark.sql("CREATE SCHEMA IF NOT EXISTS ml")
    if not spark.catalog.tableExists(MONITORING_TABLE):
        spark.createDataFrame(
            [],
            "model_name string, model_version string, monitor_window_start_utc timestamp, monitor_window_end_utc timestamp, metric_name string, metric_value double, threshold_value double, status string, action string, feature_version string, created_at_utc timestamp"
        ).write.format("delta").saveAsTable(MONITORING_TABLE)
    if not spark.catalog.tableExists(DRIFT_TABLE):
        spark.createDataFrame(
            [],
            "model_name string, model_version string, feature_name string, baseline_row_count long, recent_row_count long, psi_value double, severity string, baseline_window_start_utc timestamp, recent_window_start_utc timestamp, recent_window_end_utc timestamp, feature_version string, created_at_utc timestamp"
        ).write.format("delta").saveAsTable(DRIFT_TABLE)
    if not spark.catalog.tableExists(EXPLANATION_TABLE):
        spark.createDataFrame(
            [],
            "model_name string, model_version string, feature_name string, feature_importance double, importance_rank int, explanation_method string, feature_version string, created_at_utc timestamp"
        ).write.format("delta").saveAsTable(EXPLANATION_TABLE)


ensure_output_tables()

predictions = spark.table(PREDICTION_TABLE)
training = spark.table(TRAINING_TABLE).where(F.col("label_valid") == True)
audit = spark.table(TRAINING_AUDIT_TABLE).orderBy(F.col("created_at_utc").desc()).limit(1)
audit_row = audit.first()
if audit_row is None:
    raise RuntimeError("No registered-model training audit row exists")

MODEL_VERSION = str(audit_row["registered_model_version"])
now = datetime.now(timezone.utc)
recent_start = now - timedelta(days=RECENT_DAYS)
baseline_start = now - timedelta(days=BASELINE_DAYS)
recent = predictions.where(F.col("scored_at_utc") >= F.lit(recent_start))
labelled = (
    recent.join(
        spark.table(TRAINING_TABLE).select("feature_id", "label_failure_60m", "label_valid"),
        "feature_id",
        "inner",
    )
    .where(F.col("label_valid") == True)
)

monitor_rows = []
recent_count = recent.count()

if recent_count:
    predicted_machines = recent.select("machine_id").distinct().count()
coverage = predicted_machines / 270.0

monitor_rows.append({
    "model_name": MODEL_NAME,
    "model_version": MODEL_VERSION,
    "monitor_window_start_utc": recent_start,
    "monitor_window_end_utc": now,
    "metric_name": "machine_coverage",
    "metric_value": coverage,
    "threshold_value": float(THRESHOLDS["prediction_coverage_min"]),
    "status": status_from_threshold(coverage, float(THRESHOLDS["prediction_coverage_min"]), "min"),
    "action": "MODEL_REVIEW" if coverage < float(THRESHOLDS["prediction_coverage_min"]) else "NONE",
    "feature_version": FEATURE_VERSION,
})

risk_rate = (
    recent.where(F.col("risk_band") == "CRITICAL").count() / recent_count
    if recent_count else 0.0
)
monitor_rows.append({
    "model_name": MODEL_NAME,
    "model_version": MODEL_VERSION,
    "monitor_window_start_utc": recent_start,
    "monitor_window_end_utc": now,
    "metric_name": "critical_risk_rate",
    "metric_value": float(risk_rate),
    "threshold_value": float(THRESHOLDS["critical_risk_rate_max"]),
    "status": status_from_threshold(float(risk_rate), float(THRESHOLDS["critical_risk_rate_max"]), "max"),
    "action": "DATA_DRIFT_REVIEW" if risk_rate > float(THRESHOLDS["critical_risk_rate_max"]) else "NONE",
    "feature_version": FEATURE_VERSION,
})

label_count = labelled.count()
if label_count >= int(MONITOR_CFG["monitoring"]["minimum_recent_predictions"]):
    pdf = labelled.select("failure_risk_score", "label_failure_60m").toPandas()
    from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
    y_true = pdf["label_failure_60m"].astype(int)
    score = np.clip(pdf["failure_risk_score"].astype(float), 0.0, 1.0)
    roc_auc = float(roc_auc_score(y_true, score))
    average_precision = float(average_precision_score(y_true, score))
    brier = float(brier_score_loss(y_true, score))
else:
    roc_auc = average_precision = brier = float("nan")

for name, value, threshold, direction, action in [
    ("roc_auc", roc_auc, float(THRESHOLDS["roc_auc_min"]), "min", "MODEL_REVIEW"),
    ("average_precision", average_precision, float(THRESHOLDS["average_precision_min"]), "min", "MODEL_REVIEW"),
    ("brier_score", brier, float(THRESHOLDS["brier_max"]), "max", "MODEL_REVIEW"),
]:
    monitor_rows.append({
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "monitor_window_start_utc": recent_start,
        "monitor_window_end_utc": now,
        "metric_name": name,
        "metric_value": value,
        "threshold_value": threshold,
        "status": status_from_threshold(value, threshold, direction),
        "action": action if (not math.isnan(value) and status_from_threshold(value, threshold, direction) == "BREACH") else "NONE",
        "feature_version": FEATURE_VERSION,
    })

append_monitoring(monitor_rows)

feature_rows = []
recent_features = spark.table(FEATURE_TABLE).where(F.col("feature_time_utc") >= F.lit(recent_start))
baseline_features = training.where(
    (F.col("feature_time_utc") >= F.lit(baseline_start))
    & (F.col("feature_time_utc") < F.lit(recent_start))
)

for feature_name in DRIFT_FEATURES:
    if feature_name not in training.columns or feature_name not in recent_features.columns:
        continue
    baseline_pdf = baseline_features.select(feature_name).toPandas()[feature_name]
    recent_pdf = recent_features.select(feature_name).toPandas()[feature_name]
    value = psi(baseline_pdf, recent_pdf)
    severity = (
        "CRITICAL" if (not math.isnan(value) and value >= float(THRESHOLDS["psi_critical"]))
        else "WARN" if (not math.isnan(value) and value >= float(THRESHOLDS["psi_warn"]))
        else "OK"
    )
    feature_rows.append({
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "feature_name": feature_name,
        "baseline_row_count": int(baseline_features.select(feature_name).count()),
        "recent_row_count": int(recent_features.select(feature_name).count()),
        "psi_value": float(value) if not math.isnan(value) else None,
        "severity": severity,
        "baseline_window_start_utc": baseline_start,
        "recent_window_start_utc": recent_start,
        "recent_window_end_utc": now,
        "feature_version": FEATURE_VERSION,
        "created_at_utc": now,
    })

if feature_rows:
    spark.createDataFrame(feature_rows).write.format("delta").mode("append").saveAsTable(DRIFT_TABLE)

model_uri = f"models:/{MODEL_NAME}/{MODEL_VERSION}"
model = mlflow.sklearn.load_model(model_uri)
importance = getattr(model, "feature_importances_", None)
if importance is None:
    raise RuntimeError("Registered sklearn model does not expose feature_importances_")

explanation_rows = []
for rank, index in enumerate(np.argsort(importance)[::-1][:TOP_K], start=1):
    explanation_rows.append({
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "feature_name": MODEL_FEATURES[index] if index < len(MODEL_FEATURES) else f"feature_{index}",
        "feature_importance": float(importance[index]),
        "importance_rank": rank,
        "explanation_method": MONITOR_CFG["explainability"]["method"],
        "feature_version": FEATURE_VERSION,
        "created_at_utc": now,
    })

if explanation_rows:
    spark.createDataFrame(explanation_rows).write.format("delta").mode("append").saveAsTable(EXPLANATION_TABLE)

print(
    f"ML monitoring complete: model={MODEL_NAME} v{MODEL_VERSION}, "
    f"recent_predictions={recent_count}, labelled={label_count}"
)
