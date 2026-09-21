# Fabric Spark notebook: Bronze -> Silver
#
# Execution parameters should be injected by a Fabric Data Pipeline.
# The notebook is intentionally fail-closed when governed master references are unavailable.

from pyspark.sql import functions as F
from pyspark.sql.window import Window
from delta.tables import DeltaTable
from datetime import datetime, timezone


# -----------------------------
# Runtime parameters
# -----------------------------
SILVER_RUN_ID = "SLV-REPLACE_ME"
BRONZE_TABLE = "bronze_iot_event"
TELEMETRY_TABLE = "silver.machine_telemetry"
OPERATIONAL_TABLE = "silver.machine_operational_event"
PRODUCTION_TABLE = "silver.production_event"
REJECTED_TABLE = "silver.rejected_event"
AUDIT_TABLE = "control.silver_load_audit"
MASTER_MACHINE_TABLE = "mdm.dim_machine"
MASTER_LINE_TABLE = "mdm.dim_line"
MASTER_PLANT_TABLE = "mdm.dim_plant"
MASTER_PRODUCT_TABLE = "mdm.dim_product"
LATE_ARRIVAL_THRESHOLD_MINUTES = 15

spark.conf.set("spark.sql.session.timeZone", "UTC")


def table_exists(name: str) -> bool:
    return spark.catalog.tableExists(name)


def json_string(column: str, key: str):
    return F.get_json_object(column, f"$.{key}")


def json_double(column: str, key: str):
    return json_string(column, key).cast("double")


def json_long(column: str, key: str):
    return json_string(column, key).cast("long")


def json_bool(column: str, key: str):
    return json_string(column, key).cast("boolean")


def ensure_tables() -> None:
    if not table_exists(REJECTED_TABLE):
        spark.createDataFrame(
            [],
            "silver_run_id string, event_id string, event_type string, rejection_code string, rejection_detail string, ingestion_batch_id string, simulator_run_id string, event_time timestamp, ingestion_time timestamp, event_payload_json string, rejected_at_utc timestamp"
        ).write.format("delta").saveAsTable(REJECTED_TABLE)

    if not table_exists(AUDIT_TABLE):
        spark.createDataFrame(
            [],
            "silver_run_id string, processing_started_at_utc timestamp, processing_completed_at_utc timestamp, source_table string, source_window_start_utc timestamp, source_window_end_utc timestamp, source_row_count long, duplicate_row_count long, conflict_event_count long, accepted_row_count long, rejected_row_count long, late_arrival_count long, master_reference_failure_count long, status string, error_code string, details string"
        ).write.format("delta").saveAsTable(AUDIT_TABLE)

    if not table_exists(MASTER_MACHINE_TABLE) or not table_exists(MASTER_LINE_TABLE) or not table_exists(MASTER_PLANT_TABLE) or not table_exists(MASTER_PRODUCT_TABLE):
        raise RuntimeError("Required MDM tables are unavailable; Silver processing is fail-closed")


def read_bronze():
    return (
        spark.table(BRONZE_TABLE)
        .select(
            "event_id", "event_type", "schema_version", "event_time", "ingestion_time",
            "source_system", "plant_id", "line_id", "machine_id", "simulator_run_id",
            "generation_sequence", "payload_sha256", "event_payload_json", "ingestion_batch_id"
        )
        .withColumn("event_time", F.to_utc_timestamp(F.to_timestamp("event_time"), "UTC"))
        .withColumn("ingestion_time", F.to_utc_timestamp(F.to_timestamp("ingestion_time"), "UTC"))
    )


def classify_duplicates(df):
    conflict_ids = (
        df.groupBy("event_id")
        .agg(F.countDistinct("payload_sha256").alias("payload_versions"))
        .where(F.col("payload_versions") > 1)
        .select("event_id")
    )

    conflicts = df.join(conflict_ids, "event_id", "inner")
    non_conflicting = df.join(conflict_ids, "event_id", "left_anti")

    window = Window.partitionBy("event_id").orderBy(
        F.col("ingestion_time").desc_nulls_last(),
        F.col("generation_sequence").desc_nulls_last(),
        F.col("payload_sha256").desc(),
    )
    deduped = (
        non_conflicting.withColumn("duplicate_rank", F.row_number().over(window))
        .where(F.col("duplicate_rank") == 1)
        .drop("duplicate_rank")
    )
    duplicate_count = non_conflicting.count() - deduped.count()
    conflict_count = conflicts.select("event_id").distinct().count()
    return deduped, conflicts, duplicate_count, conflict_count


def add_late_arrival_flag(df):
    max_event_time = df.agg(F.max("event_time").alias("max_event_time")).first()[0]
    if max_event_time is None:
        return df.withColumn("is_late_arrival", F.lit(False))
    threshold_expr = F.expr(f"INTERVAL {LATE_ARRIVAL_THRESHOLD_MINUTES} MINUTES")
    return df.withColumn(
        "is_late_arrival",
        F.col("event_time") < F.lit(max_event_time) - threshold_expr,
    )


def enrich_master_keys(df):
    machines = spark.table(MASTER_MACHINE_TABLE).select(
        "machine_id", "machine_sk", "line_sk", "machine_type_code",
        F.col("effective_from").alias("machine_effective_from"),
        F.col("effective_to").alias("machine_effective_to"),
    )
    lines = spark.table(MASTER_LINE_TABLE).select(
        F.col("line_sk").alias("master_line_sk"),
        "line_id", "plant_sk",
    )
    plants = spark.table(MASTER_PLANT_TABLE).select(
        F.col("plant_sk").alias("master_plant_sk"),
        "plant_id",
    )
    products = spark.table(MASTER_PRODUCT_TABLE).select("product_id", "product_sk")

    if "product_id" not in df.columns:
        df = df.withColumn("product_id", json_string("event_payload_json", "product_id"))

    out = (
        df.join(
            machines,
            (df.machine_id == machines.machine_id)
            & (F.to_date(df.event_time) >= F.col("machine_effective_from"))
            & (
                F.col("machine_effective_to").isNull()
                | (F.to_date(df.event_time) <= F.col("machine_effective_to"))
            ),
            "left",
        )
        .drop(machines.machine_id)
    )
    out = out.join(lines, out.line_id == lines.line_id, "left").drop(lines.line_id)
    out = out.join(plants, out.plant_id == plants.plant_id, "left").drop(plants.plant_id)
    out = out.join(products, out.product_id == products.product_id, "left").drop(products.product_id)
    return out


def reject_rows(df):
    return df.withColumn(
        "rejection_code",
        F.when(F.col("event_id").isNull(), "MISSING_EVENT_ID")
        .when(F.col("event_time").isNull(), "INVALID_EVENT_TIME")
        .when(F.col("plant_id").isNull(), "MISSING_PLANT_ID")
        .when(
            F.col("machine_id").isNotNull() & F.col("machine_sk").isNull(),
            "MACHINE_MASTER_NOT_FOUND",
        )
        .when(
            F.col("line_id").isNotNull() & F.col("master_line_sk").isNull(),
            "LINE_MASTER_NOT_FOUND",
        )
        .when(
            F.col("product_id").isNotNull() & F.col("product_sk").isNull(),
            "PRODUCT_MASTER_NOT_FOUND",
        )
        .when(
            F.col("machine_sk").isNotNull() &
            F.col("line_sk").isNotNull() &
            (F.col("line_sk") != F.col("master_line_sk")),
            "MACHINE_LINE_MISMATCH",
        )
        .when(
            F.col("master_line_sk").isNotNull() &
            F.col("master_plant_sk").isNotNull() &
            (F.col("plant_sk") != F.col("master_plant_sk")),
            "LINE_PLANT_MISMATCH",
        )
        .when(
            F.col("actual_quantity").isNotNull() &
            ((F.col("actual_quantity") < 0) | (F.col("good_quantity") < 0) | (F.col("rejected_quantity") < 0)),
            "NEGATIVE_PRODUCTION_QUANTITY",
        )
        .when(
            F.col("actual_quantity").isNotNull() &
            F.col("good_quantity").isNotNull() &
            F.col("rejected_quantity").isNotNull() &
            ((F.col("good_quantity") + F.col("rejected_quantity")) > F.col("actual_quantity")),
            "PRODUCTION_QUANTITY_INCONSISTENCY",
        )
        .otherwise(None),
    ).withColumn(
        "rejection_detail",
        F.when(F.col("rejection_code").isNotNull(), F.concat(F.lit("Silver quality gate: "), F.col("rejection_code"))),
    )


def extract_domain_columns(df):
    payload = "event_payload_json"

    telemetry = df.where(F.col("event_type") == "MachineTelemetry").select(
        "event_id", "event_type", "schema_version", "event_time", "ingestion_time", "source_system",
        "plant_id", "line_id", "machine_id",
        json_string(payload, "correlation_id").alias("correlation_id"),
        json_string(payload, "causation_id").alias("causation_id"),
        "payload_sha256",
        json_string(payload, "machine_type").alias("machine_type"),
        json_string(payload, "operating_state").alias("operating_state"),
        json_double(payload, "temperature_c").alias("temperature_c"),
        json_double(payload, "vibration_mm_s").alias("vibration_mm_s"),
        json_double(payload, "pressure_bar").alias("pressure_bar"),
        json_double(payload, "spindle_rpm").alias("spindle_rpm"),
        json_double(payload, "power_kw").alias("power_kw"),
        json_double(payload, "production_rate_unit_min").alias("production_rate_unit_min"),
        json_double(payload, "quality_score_pct").alias("quality_score_pct"),
        json_double(payload, "feed_rate_mm_min").alias("feed_rate_mm_min"),
        json_double(payload, "hydraulic_pressure_bar").alias("hydraulic_pressure_bar"),
        json_double(payload, "force_kn").alias("force_kn"),
        json_double(payload, "cycle_time_s").alias("cycle_time_s"),
        json_double(payload, "motor_temperature_c").alias("motor_temperature_c"),
        json_double(payload, "torque_nm").alias("torque_nm"),
        json_double(payload, "position_error_mm").alias("position_error_mm"),
        json_double(payload, "motor_current_a").alias("motor_current_a"),
        json_double(payload, "belt_speed_m_s").alias("belt_speed_m_s"),
        json_double(payload, "discharge_pressure_bar").alias("discharge_pressure_bar"),
        json_double(payload, "rpm").alias("rpm"),
        json_double(payload, "chamber_temperature_c").alias("chamber_temperature_c"),
        json_double(payload, "fuel_flow_rate").alias("fuel_flow_rate"),
        json_double(payload, "pressure_mbar").alias("pressure_mbar"),
        json_double(payload, "inspection_cycle_time_s").alias("inspection_cycle_time_s"),
        json_double(payload, "measurement_deviation_mm").alias("measurement_deviation_mm"),
        json_double(payload, "defect_probability_pct").alias("defect_probability_pct"),
        json_double(payload, "equipment_temperature_c").alias("equipment_temperature_c"),
        json_double(payload, "throughput_unit_min").alias("throughput_unit_min"),
        "simulator_run_id", "scenario_id", "scenario_instance_id", "generation_sequence", "ingestion_batch_id",
        "event_payload_json", "is_late_arrival",
        F.to_date("event_time").alias("event_date"), F.current_timestamp().alias("processed_at_utc"),
    )

    operational = df.where(F.col("event_type").isin(
        "MachineStarted", "MachineStopped", "StateChanged", "AlarmRaised", "AlarmCleared",
        "MachineFaulted", "MachineRecovered", "CommunicationLost", "CommunicationRestored"
    )).select(
        "event_id", "event_type", "schema_version", "event_time", "ingestion_time", "source_system",
        "plant_id", "line_id", "machine_id",
        json_string(payload, "correlation_id").alias("correlation_id"),
        json_string(payload, "causation_id").alias("causation_id"),
        "payload_sha256",
        json_string(payload, "machine_type").alias("machine_type"),
        json_string(payload, "operating_state").alias("operating_state"),
        json_string(payload, "previous_state").alias("previous_state"),
        json_string(payload, "new_state").alias("new_state"),
        json_string(payload, "alarm_code").alias("alarm_code"),
        json_string(payload, "severity").alias("severity"),
        json_string(payload, "fault_code").alias("fault_code"),
        json_string(payload, "failure_mode_code").alias("failure_mode_code"),
        json_string(payload, "operator_id").alias("operator_id"),
        json_string(payload, "work_order_id").alias("work_order_id"),
        json_string(payload, "correlation_id").alias("correlation_id"),
        json_string(payload, "causation_id").alias("causation_id"),
        "simulator_run_id", "scenario_id", "scenario_instance_id", "generation_sequence", "ingestion_batch_id",
        "event_payload_json", "is_late_arrival",
        F.to_date("event_time").alias("event_date"), F.current_timestamp().alias("processed_at_utc"),
    )

    production = df.where(F.col("event_type").isin(
        "ProductionOrderCreated", "ProductionOrderReleased", "ProductionStarted", "BatchStarted",
        "UnitProduced", "BatchCompleted", "ProductionPaused", "ProductionResumed",
        "ProductionCompleted", "ProductionLossRecorded"
    )).select(
        "event_id", "event_type", "schema_version", "event_time", "ingestion_time", "source_system",
        "plant_id", "line_id", "machine_id",
        json_string(payload, "correlation_id").alias("correlation_id"),
        json_string(payload, "causation_id").alias("causation_id"),
        "payload_sha256",
        json_string(payload, "production_order_id").alias("production_order_id"),
        json_string(payload, "batch_id").alias("batch_id"),
        json_string(payload, "product_id").alias("product_id"),
        json_string(payload, "operation_id").alias("operation_id"),
        json_long(payload, "production_sequence").alias("production_sequence"),
        json_double(payload, "planned_quantity").alias("planned_quantity"),
        json_double(payload, "actual_quantity").alias("actual_quantity"),
        json_double(payload, "good_quantity").alias("good_quantity"),
        json_double(payload, "rejected_quantity").alias("rejected_quantity"),
        json_string(payload, "quantity_uom").alias("quantity_uom"),
        json_string(payload, "pause_reason_code").alias("pause_reason_code"),
        json_string(payload, "loss_reason_code").alias("loss_reason_code"),
        json_string(payload, "loss_category").alias("loss_category"),
        json_double(payload, "loss_quantity").alias("loss_quantity"),
        json_double(payload, "loss_duration_seconds").alias("loss_duration_seconds"),
        json_string(payload, "downtime_event_id").alias("downtime_event_id"),
        json_string(payload, "machine_fault_event_id").alias("machine_fault_event_id"),
        json_string(payload, "correlation_id").alias("correlation_id"),
        json_string(payload, "causation_id").alias("causation_id"),
        "simulator_run_id", "scenario_id", "scenario_instance_id", "generation_sequence", "ingestion_batch_id",
        "event_payload_json", "is_late_arrival",
        F.to_date("event_time").alias("event_date"), F.current_timestamp().alias("processed_at_utc"),
    )
    return telemetry, operational, production


def add_lineage(df, master_cols):
    return df.select("*", *master_cols)


def write_delta(table_name: str, df):
    if not df.take(1):
        return
    if not table_exists(table_name):
        df.write.format("delta").partitionBy("event_date").saveAsTable(table_name)
        return
    target = DeltaTable.forName(spark, table_name)
    (
        target.alias("t")
        .merge(df.alias("s"), "t.event_id = s.event_id")
        .whenMatchedUpdateAll()
        .whenNotMatchedInsertAll()
        .execute()
    )


ensure_tables()
started_at = datetime.now(timezone.utc)
bronze = read_bronze()
source_count = bronze.count()

if source_count == 0:
    raise RuntimeError("No Bronze records available for Silver processing")

deduped, conflicts, duplicate_count, conflict_count = classify_duplicates(bronze)
deduped = add_late_arrival_flag(deduped)
enriched = enrich_master_keys(deduped)

# Extract business columns needed for quality rules before writing domain tables.
enriched_for_quality = enriched.withColumn("product_id", json_string("event_payload_json", "product_id"))
enriched_for_quality = enriched_for_quality.withColumn("actual_quantity", json_double("event_payload_json", "actual_quantity"))
enriched_for_quality = enriched_for_quality.withColumn("good_quantity", json_double("event_payload_json", "good_quantity"))
enriched_for_quality = enriched_for_quality.withColumn("rejected_quantity", json_double("event_payload_json", "rejected_quantity"))
rejected = reject_rows(enriched_for_quality).where(F.col("rejection_code").isNotNull())
accepted = enriched_for_quality.where(F.col("rejection_code").isNull()).drop("rejection_code", "rejection_detail")

conflict_rejected = conflicts.select(
    F.lit(SILVER_RUN_ID).alias("silver_run_id"),
    "event_id", "event_type",
    F.lit("EVENT_ID_PAYLOAD_CONFLICT").alias("rejection_code"),
    F.lit("Same event_id was observed with multiple payload hashes").alias("rejection_detail"),
    "ingestion_batch_id", "simulator_run_id", "event_time", "ingestion_time",
    "event_payload_json", F.current_timestamp().alias("rejected_at_utc")
)

quality_rejected = rejected.select(
    F.lit(SILVER_RUN_ID).alias("silver_run_id"),
    "event_id", "event_type", "rejection_code", "rejection_detail",
    "ingestion_batch_id", "simulator_run_id", "event_time", "ingestion_time",
    "event_payload_json", F.current_timestamp().alias("rejected_at_utc")
)

all_rejected = conflict_rejected.unionByName(quality_rejected)
if all_rejected.take(1):
    all_rejected.write.mode("append").format("delta").saveAsTable(REJECTED_TABLE)

telemetry, operational, production = extract_domain_columns(accepted)

telemetry = telemetry.join(
    enriched.select("event_id", "machine_sk", "master_line_sk", "plant_sk", "master_plant_sk", "product_sk"),
    "event_id", "left"
)
operational = operational.join(
    enriched.select("event_id", "machine_sk", "master_line_sk", "plant_sk", "master_plant_sk", "product_sk"),
    "event_id", "left"
)
production = production.join(
    enriched.select("event_id", "machine_sk", "master_line_sk", "plant_sk", "master_plant_sk", "product_sk"),
    "event_id", "left"
)

write_delta(TELEMETRY_TABLE, telemetry)
write_delta(OPERATIONAL_TABLE, operational)
write_delta(PRODUCTION_TABLE, production)

accepted_count = accepted.count()
late_count = accepted.where(F.col("is_late_arrival") == True).count()
master_failure_count = quality_rejected.where(
    F.col("rejection_code").isin(
        "MACHINE_MASTER_NOT_FOUND",
        "LINE_MASTER_NOT_FOUND",
        "PRODUCT_MASTER_NOT_FOUND",
        "MACHINE_LINE_MISMATCH",
        "LINE_PLANT_MISMATCH",
    )
).count()
rejected_count = all_rejected.count()

audit = spark.createDataFrame([(
    SILVER_RUN_ID,
    source_count,
    duplicate_count,
    conflict_count,
    accepted_count,
    rejected_count,
    late_count,
    master_failure_count,
)], "silver_run_id string, source_row_count long, duplicate_row_count long, conflict_event_count long, accepted_row_count long, rejected_row_count long, late_arrival_count long, master_reference_failure_count long")
audit = audit.withColumn("processing_started_at_utc", started_at)
audit = audit.withColumn("processing_completed_at_utc", F.current_timestamp())
audit = audit.withColumn("source_table", F.lit(BRONZE_TABLE))
source_window = bronze.agg(
    F.min("event_time").alias("min_event_time"),
    F.max("event_time").alias("max_event_time"),
).first()
audit = audit.withColumn(
    "source_window_start_utc",
    F.lit(source_window["min_event_time"]).cast("timestamp"),
)
audit = audit.withColumn(
    "source_window_end_utc",
    F.lit(source_window["max_event_time"]).cast("timestamp"),
)
audit = audit.withColumn("status", F.lit("COMPLETED"))
audit = audit.withColumn("error_code", F.lit(None).cast("string"))
audit = audit.withColumn("details", F.lit("Bronze normalized, deduplicated, master-validated and routed to Silver domain Delta tables"))
audit.select(
    "silver_run_id", "processing_started_at_utc", "processing_completed_at_utc",
    "source_table", "source_window_start_utc", "source_window_end_utc",
    "source_row_count", "duplicate_row_count", "conflict_event_count",
    "accepted_row_count", "rejected_row_count", "late_arrival_count",
    "master_reference_failure_count", "status", "error_code", "details"
).write.mode("append").format("delta").saveAsTable(AUDIT_TABLE)

{
    "silver_run_id": SILVER_RUN_ID,
    "status": "COMPLETED",
    "source_row_count": source_count,
    "accepted_row_count": accepted_count,
    "rejected_row_count": rejected_count,
    "duplicate_row_count": duplicate_count,
    "conflict_event_count": conflict_count,
    "late_arrival_count": late_count,
    "master_reference_failure_count": master_failure_count,
}