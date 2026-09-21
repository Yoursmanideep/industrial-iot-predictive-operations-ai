# Fabric Spark notebook: Predictive Maintenance feature engineering + causal labels
#
# Builds 5-minute machine snapshots from Silver and creates a future-looking
# 60-minute failure label only from actual causal MachineFaulted events.

from datetime import datetime, timezone
import math
import yaml

from pyspark.sql import functions as F
from pyspark.sql.window import Window


CONFIG_PATH = "../config/predictive_maintenance_ml.yaml"
TELEMETRY_TABLE = "silver.machine_telemetry"
OPERATIONAL_TABLE = "silver.machine_operational_event"
PRODUCTION_TABLE = "silver.production_event"
MACHINE_MASTER_TABLE = "mdm.dim_machine"
FEATURE_TABLE = "ml.machine_failure_features"
TRAINING_TABLE = "ml.machine_failure_training"

spark.conf.set("spark.sql.session.timeZone", "UTC")

with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
    CFG = yaml.safe_load(handle)

FEATURE_VERSION = CFG["feature_engineering"]["feature_version"]
LABEL_VERSION = CFG["feature_engineering"]["label_version"]
LABEL_HORIZON_SECONDS = int(CFG["project"]["target_horizon_minutes"]) * 60

MACHINE_TYPE_CODE = {
    "CNC": 1,
    "HYDRAULIC_PRESS": 2,
    "INDUSTRIAL_ROBOT": 3,
    "CONVEYOR": 4,
    "COMPRESSOR": 5,
    "FURNACE": 6,
    "INSPECTION": 7,
    "PACKAGING": 8,
    "PALLETIZER": 9,
}

CORE_SIGNALS = [
    "temperature_c", "vibration_mm_s", "pressure_bar", "power_kw",
    "cycle_time_s", "throughput_unit_min", "quality_score_pct",
    "position_error_mm", "motor_current_a", "torque_nm",
]

ROLLING_SIGNALS = [
    "temperature_c", "vibration_mm_s", "pressure_bar", "power_kw",
]

SIGNAL_SOURCES = {
    "temperature_c": ["temperature_c", "motor_temperature_c", "chamber_temperature_c", "equipment_temperature_c"],
    "vibration_mm_s": ["vibration_mm_s"],
    "pressure_bar": ["pressure_bar", "hydraulic_pressure_bar", "discharge_pressure_bar"],
    "power_kw": ["power_kw"],
    "cycle_time_s": ["cycle_time_s"],
    "throughput_unit_min": ["production_rate_unit_min", "throughput_unit_min"],
    "quality_score_pct": ["quality_score_pct"],
    "position_error_mm": ["position_error_mm"],
    "motor_current_a": ["motor_current_a"],
    "torque_nm": ["torque_nm"],
]


def assert_tables():
    required = [TELEMETRY_TABLE, OPERATIONAL_TABLE, PRODUCTION_TABLE, MACHINE_MASTER_TABLE]
    missing = [name for name in required if not spark.catalog.tableExists(name)]
    if missing:
        raise RuntimeError(f"Required tables are unavailable: {missing}")


def normalized_telemetry():
    source = spark.table(TELEMETRY_TABLE).withColumn(
        "event_time_utc", F.col("event_time").cast("timestamp")
    )
    for output_name, source_names in SIGNAL_SOURCES.items():
        existing = [F.col(name) for name in source_names if name in source.columns]
        source = source.withColumn(
            output_name,
            F.coalesce(*existing) if existing else F.lit(None).cast("double"),
        )
    return source


def bucket_telemetry(source):
    bucket = F.window(F.col("event_time_utc"), "5 minutes")
    aggregations = [
        F.max_by("plant_id", "event_time_utc").alias("plant_id"),
        F.max_by("line_id", "event_time_utc").alias("line_id"),
        F.max_by("machine_type", "event_time_utc").alias("machine_type"),
        F.max_by("operating_state", "event_time_utc").alias("operating_state"),
    ]
    for signal in CORE_SIGNALS:
        aggregations.append(F.max_by(signal, "event_time_utc").alias(signal))
    return source.groupBy("machine_id", bucket.alias("time_bucket")).agg(*aggregations)


def bucket_operational_events():
    source = spark.table(OPERATIONAL_TABLE).withColumn(
        "event_time_utc", F.col("event_time").cast("timestamp")
    )
    bucket = F.window(F.col("event_time_utc"), "5 minutes")
    return source.groupBy("machine_id", bucket.alias("time_bucket")).agg(
        F.sum(F.when(F.col("event_type") == "AlarmRaised", 1).otherwise(0)).cast("int").alias("alarm_count_bucket"),
        F.sum(F.when(F.col("event_type") == "MachineFaulted", 1).otherwise(0)).cast("int").alias("fault_count_bucket"),
        F.sum(F.when(F.col("event_type") == "CommunicationLost", 1).otherwise(0)).cast("int").alias("communication_loss_count_bucket"),
    )


def bucket_line_production():
    source = spark.table(PRODUCTION_TABLE).withColumn(
        "event_time_utc", F.col("event_time").cast("timestamp")
    )
    bucket = F.window(F.col("event_time_utc"), "5 minutes")
    return (
        source.where(F.col("line_id").isNotNull())
        .groupBy("line_id", bucket.alias("time_bucket"))
        .agg(
            F.sum(F.coalesce(F.col("actual_quantity"), F.lit(0))).alias("line_actual_quantity_bucket"),
            F.sum(F.coalesce(F.col("loss_quantity"), F.lit(0))).alias("line_loss_quantity_bucket"),
        )
    )


def add_time_context(features):
    local_hour = F.hour(F.from_utc_timestamp(F.col("feature_time_utc"), "Asia/Kolkata"))
    radians = (local_hour.cast("double") / F.lit(24.0)) * F.lit(2.0 * math.pi)
    mapping = F.create_map(
        [F.lit(item) for pair in MACHINE_TYPE_CODE.items() for item in pair]
    )
    return (
        features
        .withColumn(
            "shift_code",
            F.when((local_hour >= 6) & (local_hour < 14), 1)
            .when((local_hour >= 14) & (local_hour < 22), 2)
            .otherwise(3),
        )
        .withColumn("hour_sin", F.sin(radians))
        .withColumn("hour_cos", F.cos(radians))
        .withColumn("machine_type_code", mapping[F.col("machine_type")].cast("int"))
    )


def add_rolling_features(features):
    features = features.withColumn("feature_epoch", F.col("feature_time_utc").cast("long"))
    for label, seconds in (("15m", 900), ("60m", 3600)):
        machine_window = (
            Window.partitionBy("machine_id")
            .orderBy("feature_epoch")
            .rangeBetween(-seconds, 0)
        )
        line_window = (
            Window.partitionBy("line_id")
            .orderBy("feature_epoch")
            .rangeBetween(-seconds, 0)
        )
        for signal in ROLLING_SIGNALS:
            features = features.withColumn(
                f"{signal}_mean_{label}", F.avg(signal).over(machine_window)
            )
            features = features.withColumn(
                f"{signal}_std_{label}", F.stddev_pop(signal).over(machine_window)
            )
            features = features.withColumn(
                f"{signal}_delta_{label}",
                F.col(signal) - F.first(signal, ignorenulls=True).over(machine_window),
            )
        features = features.withColumn(
            f"alarm_count_{label}", F.sum("alarm_count_bucket").over(machine_window).cast("int")
        )
        features = features.withColumn(
            f"line_actual_quantity_{label}", F.sum("line_actual_quantity_bucket").over(line_window)
        )
        features = features.withColumn(
            f"line_loss_quantity_{label}", F.sum("line_loss_quantity_bucket").over(line_window)
        )
        if label == "60m":
            features = features.withColumn(
                "communication_loss_count_60m",
                F.sum("communication_loss_count_bucket").over(machine_window).cast("int"),
            )

    fault_window = (
        Window.partitionBy("machine_id")
        .orderBy("feature_epoch")
        .rangeBetween(-86400, 0)
    )
    utilization_window = (
        Window.partitionBy("machine_id")
        .orderBy("feature_epoch")
        .rangeBetween(-900, 0)
    )
    return (
        features
        .withColumn("fault_count_24h", F.sum("fault_count_bucket").over(fault_window).cast("int"))
        .withColumn(
            "utilization_proxy_15m",
            F.avg(
                F.when(F.col("operating_state") == "RUNNING", 1.0).otherwise(0.0)
            ).over(utilization_window),
        )
        .drop("feature_epoch")
    )


def add_machine_age(features):
    master = (
        spark.table(MACHINE_MASTER_TABLE)
        .where(F.col("is_current") == True)
        .select("machine_id", "installation_date")
    )
    return features.join(master, "machine_id", "left").withColumn(
        "machine_age_days",
        F.when(
            F.col("installation_date").isNotNull(),
            F.datediff(F.to_date("feature_time_utc"), F.col("installation_date")).cast("double"),
        ),
    ).drop("installation_date")


def build_features():
    telemetry = bucket_telemetry(normalized_telemetry()).withColumn(
        "feature_time_utc", F.col("time_bucket.end")
    )
    ops = bucket_operational_events()
    production = bucket_line_production()
    features = telemetry.join(ops, ["machine_id", "time_bucket"], "left")
    features = features.join(production, ["line_id", "time_bucket"], "left")
    features = features.fillna(
        {
            "alarm_count_bucket": 0,
            "fault_count_bucket": 0,
            "communication_loss_count_bucket": 0,
            "line_actual_quantity_bucket": 0.0,
            "line_loss_quantity_bucket": 0.0,
        }
    )
    features = add_time_context(features)
    features = add_rolling_features(features)
    features = add_machine_age(features)
    return features.withColumn(
        "feature_id",
        F.sha2(
            F.concat_ws(
                "|",
                "machine_id",
                F.col("feature_time_utc").cast("string"),
                F.lit(FEATURE_VERSION),
            ),
            256,
        ),
    ).withColumn("feature_version", F.lit(FEATURE_VERSION))


def generate_causal_labels(features):
    faults = (
        spark.table(OPERATIONAL_TABLE)
        .where(F.col("event_type") == "MachineFaulted")
        .select(
            "machine_id",
            F.col("event_time").cast("timestamp").alias("fault_time_utc"),
            F.col("event_id").alias("fault_event_id"),
            "failure_mode_code",
        )
    )
    joined = (
        features.alias("f")
        .join(
            faults.alias("x"),
            (F.col("f.machine_id") == F.col("x.machine_id"))
            & (F.col("x.fault_time_utc") > F.col("f.feature_time_utc"))
            & (
                F.col("x.fault_time_utc")
                <= F.col("f.feature_time_utc") + F.expr("INTERVAL 60 MINUTES")
            ),
            "left",
        )
        .groupBy("f.feature_id", "f.feature_time_utc")
        .agg(
            F.min("x.fault_time_utc").alias("next_fault_time_utc"),
            F.min("x.fault_event_id").alias("next_fault_event_id"),
            F.first("x.failure_mode_code", ignorenulls=True).alias("label_failure_mode_code"),
        )
    )
    source_max = features.agg(F.max("feature_time_utc")).first()[0]
    return (
        joined
        .withColumn("label_failure_60m", F.when(F.col("next_fault_time_utc").isNotNull(), 1).otherwise(0))
        .withColumn(
            "right_censored",
            F.col("next_fault_time_utc").isNull()
            & (F.col("feature_time_utc") > F.lit(source_max) - F.expr("INTERVAL 60 MINUTES")),
        )
        .withColumn("label_valid", ~F.col("right_censored"))
        .withColumn("label_version", F.lit(LABEL_VERSION))
        .withColumn("label_horizon_minutes", F.lit(60))
        .withColumn("label_source", F.lit("CAUSAL_MACHINE_FAULT_EVENT"))
        .withColumn("label_generated_at_utc", F.current_timestamp())
        .select(
            "feature_id", "label_version", "label_horizon_minutes",
            "label_failure_60m", "label_valid",
            "next_fault_event_id", "next_fault_time_utc",
            "label_failure_mode_code", "label_source",
            "label_generated_at_utc", "right_censored",
        )
    )


assert_tables()
feature_df = build_features()
label_df = generate_causal_labels(feature_df)
training_df = feature_df.join(label_df, "feature_id", "inner")

feature_df.write.format("delta").mode("overwrite").option(
    "overwriteSchema", "true"
).saveAsTable(FEATURE_TABLE)

training_df.write.format("delta").mode("overwrite").option(
    "overwriteSchema", "true"
).saveAsTable(TRAINING_TABLE)

print(
    f"Feature engineering complete: features={feature_df.count()}, "
    f"training_rows={training_df.count()}"
)
