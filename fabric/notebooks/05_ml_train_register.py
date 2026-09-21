# Fabric Spark notebook: train, validate and register predictive-maintenance model
#
# Continuous risk score is learned from binary failure labels. Tree regressors
# are endpoint-friendly sklearn models supported by the current Fabric endpoint path.

from datetime import datetime, timezone

import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
import yaml
from mlflow.models import infer_signature
from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor
from sklearn.metrics import average_precision_score, brier_score_loss, mean_squared_error, roc_auc_score, precision_recall_curve

from pyspark.sql import functions as F


CONFIG_PATH = "../config/predictive_maintenance_ml.yaml"
TRAINING_TABLE = "ml.machine_failure_training"
AUDIT_TABLE = "ml.machine_failure_training_run"

with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
    CFG = yaml.safe_load(handle)

FEATURE_VERSION = CFG["feature_engineering"]["feature_version"]
LABEL_VERSION = CFG["feature_engineering"]["label_version"]
EXPERIMENT_NAME = CFG["model_registry"]["experiment_name"]
MODEL_NAME = CFG["model_registry"]["model_name"]
SEED = int(CFG["training"]["random_seed"])

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


def metric_bundle(y_true, score):
    score = np.clip(np.asarray(score, dtype=float), 0.0, 1.0)
    return {
        "roc_auc": float(roc_auc_score(y_true, score)),
        "average_precision": float(average_precision_score(y_true, score)),
        "rmse": float(mean_squared_error(y_true, score, squared=False)),
        "brier": float(brier_score_loss(y_true, score)),
    }


def threshold_for_recall(y_true, score, minimum_recall):
    precision, recall, thresholds = precision_recall_curve(y_true, score)
    valid = np.where(recall[:-1] >= minimum_recall)[0]
    if len(valid) == 0:
        return 0.50
    best_idx = valid[np.argmax(precision[:-1][valid])]
    return float(thresholds[best_idx])


def build_candidate(name, params):
    common = dict(
        n_estimators=int(params["n_estimators"]),
        max_depth=int(params["max_depth"]),
        min_samples_leaf=int(params["min_samples_leaf"]),
        max_features=params["max_features"],
        random_state=SEED,
        n_jobs=-1,
    )
    if name == "random_forest":
        return RandomForestRegressor(**common)
    if name == "extra_trees":
        return ExtraTreesRegressor(**common)
    raise ValueError(f"Unsupported candidate: {name}")


def deterministic_cap(df, limit):
    if df.count() <= limit:
        return df
    return (
        df.withColumn(
            "_stable_order",
            F.sha2(
                F.concat_ws("|", "machine_id", F.col("feature_time_utc").cast("string")),
                256,
            ),
        )
        .orderBy("_stable_order")
        .drop("_stable_order")
        .limit(limit)
    )


def balanced_sample(df):
    max_rows = int(CFG["training"]["max_training_rows"])
    ratio = int(CFG["training"]["negative_to_positive_ratio"])
    positives = deterministic_cap(
        df.where(F.col("label_failure_60m") == 1),
        max(1, max_rows // (ratio + 1)),
    )
    positive_count = positives.count()
    negatives = deterministic_cap(
        df.where(F.col("label_failure_60m") == 0),
        max_rows - positive_count,
    )
    return positives.unionByName(negatives)


def chronological_split(dataset):
    min_time, max_time = dataset.select(
        F.min("feature_time_utc"), F.max("feature_time_utc")
    ).first()
    total_seconds = (max_time - min_time).total_seconds()
    train_end = min_time + pd.to_timedelta(
        total_seconds * float(CFG["training"]["time_split"]["train_fraction"]),
        unit="s",
    ).to_pytimedelta()
    validation_end = min_time + pd.to_timedelta(
        total_seconds * (
            float(CFG["training"]["time_split"]["train_fraction"])
            + float(CFG["training"]["time_split"]["validation_fraction"])
        ),
        unit="s",
    ).to_pytimedelta()
    return (
        dataset.where(F.col("feature_time_utc") < F.lit(train_end)),
        dataset.where(
            (F.col("feature_time_utc") >= F.lit(train_end))
            & (F.col("feature_time_utc") < F.lit(validation_end))
        ),
        dataset.where(F.col("feature_time_utc") >= F.lit(validation_end)),
    )


def to_pandas(df):
    return df.select(
        ["feature_time_utc", "machine_id", *FEATURE_COLUMNS, "label_failure_60m"]
    ).toPandas()


source = (
    spark.table(TRAINING_TABLE)
    .where(F.col("label_valid") == True)
    .where(~F.col("operating_state").isin(["FAULT", "MAINTENANCE"]))
)

train_spark, validation_spark, test_spark = chronological_split(source)
train_pd = to_pandas(balanced_sample(train_spark))
validation_pd = to_pandas(validation_spark)
test_pd = to_pandas(test_spark)

X_train = train_pd[FEATURE_COLUMNS]
y_train = train_pd["label_failure_60m"].astype(int)
X_validation = validation_pd[FEATURE_COLUMNS]
y_validation = validation_pd["label_failure_60m"].astype(int)
X_test = test_pd[FEATURE_COLUMNS]
y_test = test_pd["label_failure_60m"].astype(int)

if min(int(y_train.sum()), int(y_validation.sum()), int(y_test.sum())) == 0:
    raise RuntimeError("Every split must contain positive failure examples")

mlflow.set_experiment(EXPERIMENT_NAME)
mlflow.autolog(log_models=False)

candidate_results = []

for candidate_name, params in CFG["training"]["candidate_models"].items():
    model = build_candidate(candidate_name, params)
    with mlflow.start_run(run_name=f"candidate_{candidate_name}") as run:
        model.fit(X_train, y_train)
        validation_score = np.clip(model.predict(X_validation), 0.0, 1.0)
        metrics = metric_bundle(y_validation, validation_score)
        threshold = threshold_for_recall(
            y_validation,
            validation_score,
            float(CFG["training"]["min_validation_recall"]),
        )
        mlflow.log_params({
            "candidate": candidate_name,
            "feature_version": FEATURE_VERSION,
            "label_version": LABEL_VERSION,
            "target_horizon_minutes": 60,
            **{f"model_{key}": value for key, value in params.items()},
        })
        mlflow.log_metrics(metrics | {"operational_threshold": threshold})
        mlflow.set_tags({
            "stage": "3.16",
            "target": "MachineFaulted_within_60m",
            "leakage_control": "scenario_metadata_excluded",
        })
        mlflow.sklearn.log_model(
            model,
            "candidate_model",
            signature=infer_signature(X_validation.head(20), validation_score[:20]),
            input_example=X_validation.head(5),
        )
        candidate_results.append({
            "candidate": candidate_name,
            "run_id": run.info.run_id,
            **metrics,
        })

best = sorted(
    candidate_results,
    key=lambda row: (-row["average_precision"], -row["roc_auc"], row["rmse"]),
)[0]

train_validation_pd = pd.concat([train_pd, validation_pd], ignore_index=True)
X_train_validation = train_validation_pd[FEATURE_COLUMNS]
y_train_validation = train_validation_pd["label_failure_60m"].astype(int)
champion_model = build_candidate(
    best["candidate"],
    CFG["training"]["candidate_models"][best["candidate"]],
)

with mlflow.start_run(run_name=f"champion_{best['candidate']}") as run:
    champion_model.fit(X_train_validation, y_train_validation)
    test_score = np.clip(champion_model.predict(X_test), 0.0, 1.0)
    test_metrics = metric_bundle(y_test, test_score)

    validation_model = build_candidate(
        best["candidate"],
        CFG["training"]["candidate_models"][best["candidate"]],
    )
    validation_model.fit(X_train, y_train)
    validation_score = np.clip(validation_model.predict(X_validation), 0.0, 1.0)
    operational_threshold = threshold_for_recall(
        y_validation,
        validation_score,
        float(CFG["training"]["min_validation_recall"]),
    )

    mlflow.log_params({
        "champion_candidate": best["candidate"],
        "feature_version": FEATURE_VERSION,
        "label_version": LABEL_VERSION,
        "target_horizon_minutes": 60,
        "operational_threshold": operational_threshold,
        "train_rows": len(train_pd),
        "validation_rows": len(validation_pd),
        "test_rows": len(test_pd),
    })
    mlflow.log_metrics({
        "test_roc_auc": test_metrics["roc_auc"],
        "test_average_precision": test_metrics["average_precision"],
        "test_rmse": test_metrics["rmse"],
        "test_brier": test_metrics["brier"],
    })
    mlflow.set_tags({
        "registered_model_name": MODEL_NAME,
        "serving_flavor": "sklearn",
        "endpoint_compatible": "true",
        "feature_version": FEATURE_VERSION,
        "label_version": LABEL_VERSION,
    })

    mlflow.sklearn.log_model(
        champion_model,
        "failure_risk_model",
        signature=infer_signature(X_train_validation.head(20), test_score[:20]),
        input_example=X_train_validation.head(5),
    )
    registration_uri = f"runs:/{run.info.run_id}/failure_risk_model"
    registered = mlflow.register_model(registration_uri, MODEL_NAME)
    version = str(registered.version)

    spark.createDataFrame([{
        "training_run_id": run.info.run_id,
        "registered_model_name": MODEL_NAME,
        "registered_model_version": version,
        "candidate_model": best["candidate"],
        "feature_version": FEATURE_VERSION,
        "label_version": LABEL_VERSION,
        "operational_threshold": float(operational_threshold),
        "test_roc_auc": float(test_metrics["roc_auc"]),
        "test_average_precision": float(test_metrics["average_precision"]),
        "test_rmse": float(test_metrics["rmse"]),
        "test_brier": float(test_metrics["brier"]),
        "created_at_utc": datetime.now(timezone.utc),
    }]).write.format("delta").mode("append").saveAsTable(AUDIT_TABLE)

    print(
        f"Registered {MODEL_NAME} version {version}; "
        f"candidate={best['candidate']}; test_metrics={test_metrics}"
    )
