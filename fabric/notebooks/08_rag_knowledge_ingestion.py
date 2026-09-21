# Fabric notebook: ingest, chunk and embed Industrial IoT knowledge
#
# Versioned knowledge is copied into the Lakehouse Files area during deployment.
# Fabric AI Functions provide embeddings; Azure AI Search is the retrieval index.

import synapse.ml.spark.aifunc as aifunc
from pyspark.sql import functions as F


KNOWLEDGE_PATH = "Files/knowledge_base"
CHUNK_TABLE = "ml.rag_knowledge_chunks"
EMBED_TABLE = "ml.rag_knowledge_embeddings"


def load_documents():
    return (
        spark.read.text(f"{KNOWLEDGE_PATH}/*.md")
        .groupBy(F.input_file_name().alias("source_uri"))
        .agg(F.concat_ws("\n", F.collect_list("value")).alias("document_text"))
    )


def build_chunks():
    documents = load_documents()
    return (
        documents
        .withColumn("document_id", F.regexp_extract("document_text", r"Document ID: (DOC-[A-Z0-9-]+)", 1))
        .withColumn("document_version", F.regexp_extract("document_text", r"Version: ([0-9]+\\.[0-9]+\\.[0-9]+)", 1))
        .withColumn("title", F.regexp_extract("document_text", r"# (.+)", 1))
        .withColumn("knowledge_domain", F.regexp_extract("document_text", r"Knowledge domain: ([A-Z_]+)", 1))
        .withColumn("machine_type_code", F.regexp_extract("document_text", r"Machine type: ([A-Z_]+|null)", 1))
        .withColumn("chunk_text", F.substring("document_text", 1, 7000))
        .withColumn("heading_path", F.col("title"))
        .withColumn("source_locator", F.lit("document"))
        .withColumn("active", F.lit(True))
        .withColumn(
            "visibility_scope",
            F.when(F.col("machine_type_code") == "null", "ENTERPRISE").otherwise("MACHINE_TYPE"),
        )
        .withColumn(
            "visibility_value",
            F.when(F.col("machine_type_code") == "null", F.lit(None)).otherwise(F.col("machine_type_code")),
        )
        .withColumn(
            "chunk_id",
            F.concat(
                F.lit("KCH-"),
                F.substring(F.sha2(F.concat_ws("|", "document_id", "document_version", "source_uri"), 256), 1, 32),
            ),
        )
        .select(
            "chunk_id","document_id","document_version","title","knowledge_domain",
            "machine_type_code","heading_path","chunk_text","source_uri","source_locator",
            "active","visibility_scope","visibility_value",
        )
    )


chunks = build_chunks()

chunks.write.format("delta").mode("overwrite").option(
    "overwriteSchema", "true"
).saveAsTable(CHUNK_TABLE)

embedded = chunks.ai.embed(input_col="chunk_text", output_col="embedding")
embedded.write.format("delta").mode("overwrite").option(
    "overwriteSchema", "true"
).saveAsTable(EMBED_TABLE)

print(f"Knowledge ingestion complete: chunks={chunks.count()}")
