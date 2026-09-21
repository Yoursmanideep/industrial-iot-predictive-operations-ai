# Fabric Spark notebook: batch scoring with the registered predictive-maintenance model

import yaml
from pyspark.sql import functions as F
from synapse.ml.predict import MLFlowTransformer


CONFIG_PATH = "../config/predictive_maintenance_ml.yaml"
FEATURE_TABLE = "ml.machine_failure_features"
PREDICTION_TABLE = "ml.machine_failure_prediction"

MODEL_NAME = None
MODEL_VERSION = None
SCORING_WINDOW_START_UTC = None
SCORING_WINDOW_END_UTC = None

with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
    CFG = yaml.safe_load(handle)

FEATURE_VERSION = CFG["feature_engineering"]["feature_version"]
HORIZON_MINUTES = int(CFG["prediction"]["horizon_minutes"])

FEATURE_COLUMNS = [
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


def load_features():
    df = spark.table(FEATURE_TABLE)
    if SCORING_WINDOW_START_UTC:
        df = df.where(F.col("feature_time_utc") >= F.to_timestamp(F.lit(SCORING_WINDOW_START_UTC)))
    if SCORING_WINDOW_END_UTC:
        df = df.where(F.col("feature_time_utc") < F.to_timestamp(F.lit(SCORING_WINDOW_END_UTC)))
    return df


def risk_band(score):
    return (
        F.when(score >= F.lit(0.80), "CRITICAL")
        .when(score >= F.lit(0.60), "HIGH")
        .when(score >= F.lit(0.35), "MEDIUM")
        .otherwise("LOW")
    )


if not MODEL_NAME or not MODEL_VERSION:
    raise RuntimeError("MODEL_NAME and MODEL_VERSION are required")

features = load_features()

transformer = MLFlowTransformer(
    inputCols=FEATURE_COLUMNS,
    outputCol="prediction",
    modelName=MODEL_NAME,
    modelVersion=int(MODEL_VERSION),
)

scored = transformer.transform(
    features.select(
        "feature_id", "feature_version", "feature_time_utc",
        "plant_id", "line_id", "machine_id", *FEATURE_COLUMNS,
    )
)

output = (
    scored
    .withColumn(
        "failure_risk_score",
        F.greatest(F.lit(0.0), F.least(F.lit(1.0), F.col("prediction").cast("double"))),
    )
    .withColumn("risk_band", risk_band(F.col("failure_risk_score")))
    .withColumn("prediction_created_at_utc", F.current_timestamp())
    .withColumn("prediction_horizon_minutes", F.lit(HORIZON_MINUTES))
    .withColumn("model_name", F.lit(MODEL_NAME))
    .withColumn("model_version", F.lit(str(MODEL_VERSION)))
    .withColumn("inference_mode", F.lit("BATCH"))
    .withColumn("endpoint_reference", F.lit(None).cast("string"))
    .withColumn("source_run_id", F.lit(None).cast("string"))
    .withColumn(
        "prediction_id",
        F.sha2(
            F.concat_ws("|", "feature_id", F.lit(MODEL_NAME), F.lit(str(MODEL_VERSION)), F.lit("BATCH")),
            256,
        ),
    )
    .select(
        "prediction_id", "feature_id", "plant_id", "line_id", "machine_id",
        "feature_time_utc", "prediction_created_at_utc",
        "model_name", "model_version", "feature_version",
        "prediction_horizon_minutes", "failure_risk_score", "risk_band",
        "inference_mode", "endpoint_reference", "source_run_id",
    )
)

(
    output
    .withColumn("prediction_date", F.to_date("feature_time_utc"))
    .write.format("delta")
    .mode("append")
    .partitionBy("prediction_date", "plant_id")
    .saveAsTable(PREDICTION_TABLE)
)

print(f"Batch scoring complete; rows={output.count()}; model={MODEL_NAME} v{MODEL_VERSION}")
