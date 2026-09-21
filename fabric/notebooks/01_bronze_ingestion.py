# Fabric Spark notebook: validated simulator -> Bronze Delta
# Parameterize SOURCE_PATH and INGESTION_BATCH_ID from the pipeline/orchestrator.

from pyspark.sql import functions as F
from delta.tables import DeltaTable

SOURCE_PATH = "Files/ingress/validated/event_type=telemetry/event_date=2026-09-21/plant_id=PLT-CHN-01/telemetry.jsonl"
INGESTION_BATCH_ID = "IBT-REPLACE_ME"
BRONZE_TABLE = "bronze_iot_event"
CHECKPOINT_TABLE = "control_ingestion_batch_checkpoint"
QUARANTINE_PATH = "Files/quarantine/fabric-ingestion"


def table_exists(name: str) -> bool:
    return spark.catalog.tableExists(name)


def ensure_control_tables() -> None:
    if not table_exists(CHECKPOINT_TABLE):
        spark.createDataFrame(
            [],
            "ingestion_batch_id string, simulator_run_id string, source_file_sha256 string, event_count long, accepted_event_count long, rejected_event_count long, status string, error_code string, updated_at_utc timestamp, destination_path string"
        ).write.format("delta").saveAsTable(CHECKPOINT_TABLE)


def ensure_bronze_table() -> None:
    if not table_exists(BRONZE_TABLE):
        spark.createDataFrame(
            [],
            "event_id string, event_type string, schema_version string, event_time timestamp, ingestion_time timestamp, source_system string, plant_id string, line_id string, machine_id string, simulator_run_id string, generation_sequence long, payload_sha256 string, event_payload_json string, ingestion_batch_id string, event_date date, ingested_at_utc timestamp"
        ).write.format("delta").partitionBy("event_date").saveAsTable(BRONZE_TABLE)


def ingest_partition(source_path: str, batch_id: str) -> dict:
    ensure_control_tables()
    ensure_bronze_table()

    existing_batch = (
        spark.table(CHECKPOINT_TABLE)
        .where(F.col("ingestion_batch_id") == batch_id)
        .where(F.col("status") == "COMPLETED")
        .limit(1)
        .count()
    )
    if existing_batch:
        return {"status": "SKIPPED_DUPLICATE", "ingestion_batch_id": batch_id}

    raw = (
        spark.read.text(source_path)
        .where(F.length(F.trim(F.col("value"))) > 0)
        .withColumn("event_payload_json", F.col("value"))
        .withColumn("payload_sha256", F.sha2(F.col("value"), 256))
    )
    staged = raw.select(
        F.get_json_object("value", "$.event_id").alias("event_id"),
        F.get_json_object("value", "$.event_type").alias("event_type"),
        F.get_json_object("value", "$.schema_version").alias("schema_version"),
        F.to_timestamp(F.get_json_object("value", "$.event_time")).alias("event_time"),
        F.to_timestamp(F.get_json_object("value", "$.ingestion_time")).alias("ingestion_time"),
        F.get_json_object("value", "$.source_system").alias("source_system"),
        F.get_json_object("value", "$.plant_id").alias("plant_id"),
        F.get_json_object("value", "$.line_id").alias("line_id"),
        F.get_json_object("value", "$.machine_id").alias("machine_id"),
        F.get_json_object("value", "$.simulator_run_id").alias("simulator_run_id"),
        F.get_json_object("value", "$.generation_sequence").cast("long").alias("generation_sequence"),
        F.col("payload_sha256"),
        F.col("event_payload_json"),
    ).withColumn("event_date", F.to_date("event_time"))

    existing = spark.table(BRONZE_TABLE).select("event_id", "payload_sha256")
    joined = staged.join(existing, "event_id", "left").withColumnRenamed("payload_sha256", "existing_payload_sha256")
    conflicts = joined.where(
        F.col("existing_payload_sha256").isNotNull() &
        (F.col("existing_payload_sha256") != F.col("payload_sha256"))
    )
    conflict_count = conflicts.count()

    if conflict_count:
        (
            conflicts.withColumn("ingestion_batch_id", F.lit(batch_id))
            .write.mode("append").format("json").save(QUARANTINE_PATH)
        )

    new_events = joined.where(F.col("existing_payload_sha256").isNull()).drop("existing_payload_sha256")
    accepted_count = new_events.count()
    ingested = new_events.withColumn("ingestion_batch_id", F.lit(batch_id)).withColumn("ingested_at_utc", F.current_timestamp())

    if accepted_count:
        ingested.write.mode("append").format("delta").saveAsTable(BRONZE_TABLE)

    status = "QUARANTINED" if conflict_count else "COMPLETED"
    checkpoint = spark.createDataFrame(
        [(
            batch_id,
            staged.select("simulator_run_id").first()[0],
            None,
            staged.count(),
            accepted_count,
            conflict_count,
            status,
            "EVENT_ID_PAYLOAD_CONFLICT" if conflict_count else None,
        )],
        "ingestion_batch_id string, simulator_run_id string, source_file_sha256 string, event_count long, accepted_event_count long, rejected_event_count long, status string, error_code string"
    ).withColumn("updated_at_utc", F.current_timestamp()).withColumn("destination_path", F.lit(BRONZE_TABLE))
    checkpoint.write.mode("append").format("delta").saveAsTable(CHECKPOINT_TABLE)

    return {
        "status": status,
        "ingestion_batch_id": batch_id,
        "accepted_event_count": accepted_count,
        "conflict_event_count": conflict_count,
    }


result = ingest_partition(SOURCE_PATH, INGESTION_BATCH_ID)
result