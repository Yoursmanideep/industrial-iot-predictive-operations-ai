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
    return spark.read.text(f"{KNOWLEDGE_PATH}/*.md").groupBy(
        F.input_file_name().alias("source_uri")
    ).agg(F.concat_ws("\n", F.collect_list("value")).alias("document_text"))


def section_aware_chunks(document):
    import re

    text = document["document_text"]
    source_uri = document["source_uri"]
    doc_id = re.search(r"Document ID: (DOC-[A-Z0-9-]+)", text)
    version = re.search(r"Version: ([0-9]+\\.[0-9]+\\.[0-9]+)", text)
    title = re.search(r"# (.+)", text)
    domain = re.search(r"Knowledge domain: ([A-Z_]+)", text)
    machine = re.search(r"Machine type: ([A-Z_]+|null)", text)

    document_id = doc_id.group(1) if doc_id else "DOC-UNKNOWN"
    document_version = version.group(1) if version else "0.0.0"
    doc_title = title.group(1).strip() if title else "Untitled"
    knowledge_domain = domain.group(1) if domain else "STANDARD_OPERATING_PROCEDURE"
    machine_type = machine.group(1) if machine else "null"

    sections = re.split(r"(?m)^##\\s+", text)
    output = []
    target_words = 520
    overlap_words = 80

    for section in sections:
        words = section.strip().split()
        if not words:
            continue
        heading = words[0]
        body = words[1:]
        start = 0
        while start < len(body):
            end_pos = min(len(body), start + target_words)
            chunk_words = body[start:end_pos]
            chunk_text = " ".join(chunk_words)
            output.append({
                "document_id": document_id,
                "document_version": document_version,
                "title": doc_title,
                "knowledge_domain": knowledge_domain,
                "machine_type_code": None if machine_type == "null" else machine_type,
                "heading_path": f"{doc_title} > {heading}",
                "chunk_text": chunk_text,
                "source_uri": source_uri,
                "source_locator": f"section:{heading};words:{start}-{end_pos}",
                "active": True,
                "visibility_scope": "ENTERPRISE" if machine_type == "null" else "MACHINE_TYPE",
                "visibility_value": None if machine_type == "null" else machine_type,
            })
            if end_pos >= len(body):
                break
            start = max(0, end_pos - overlap_words)

    return output


def build_chunks():
    schema = """
        document_id string,
        document_version string,
        title string,
        knowledge_domain string,
        machine_type_code string,
        heading_path string,
        chunk_text string,
        source_uri string,
        source_locator string,
        active boolean,
        visibility_scope string,
        visibility_value string
    """
    rows = load_documents().rdd.flatMap(section_aware_chunks)
    return (
        spark.createDataFrame(rows, schema=schema)
        .withColumn(
            "chunk_id",
            F.concat(
                F.lit("KCH-"),
                F.substring(
                    F.sha2(
                        F.concat_ws(
                            "|",
                            "document_id",
                            "document_version",
                            "source_uri",
                            "source_locator",
                            "chunk_text",
                        ),
                        256,
                    ),
                    1,
                    32,
                ),
            ),
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
