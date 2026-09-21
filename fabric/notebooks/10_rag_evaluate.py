# Fabric notebook: RAG benchmark preparation and evaluation storage
#
# Retrieval and answer generation are executed by the deployed assistant.
# This notebook provides the repeatable benchmark dataset and evaluation schema.

import json
from datetime import datetime, timezone

from pyspark.sql import Row, functions as F


BENCHMARK_PATH = "Files/rag_eval/rag_eval_questions.jsonl"
EVAL_TABLE = "ml.rag_evaluation_results"

rows = []
for raw in spark.read.text(BENCHMARK_PATH).toLocalIterator():
    item = json.loads(raw["value"])
    rows.append(
        Row(
            question_id=item["question_id"],
            question=item["question"],
            expected_documents=item["expected_documents"],
            category=item["category"],
            evaluated_at_utc=datetime.now(timezone.utc),
        )
    )

benchmark = spark.createDataFrame(rows)

evaluation = (
    benchmark
    .withColumn("retrieved_documents", F.lit(None).cast("array<string>"))
    .withColumn("retrieval_score", F.lit(None).cast("double"))
    .withColumn("citation_document_match", F.lit(None).cast("boolean"))
    .withColumn("citation_chunk_match", F.lit(None).cast("boolean"))
    .withColumn("groundedness", F.lit(None).cast("double"))
    .withColumn("relevance", F.lit(None).cast("double"))
    .withColumn("answer_completeness", F.lit(None).cast("double"))
    .withColumn("answer_status", F.lit(None).cast("string"))
)

(
    evaluation.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(EVAL_TABLE)
)

print(f"RAG benchmark prepared: cases={benchmark.count()}")
