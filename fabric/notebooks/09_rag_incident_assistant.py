# Fabric notebook: grounded Industrial IoT maintenance assistant
#
# Retrieval uses Azure AI Search hybrid/vector search. Generation is constrained
# to retrieved knowledge and structured operational context.

import json
import os
import uuid
from datetime import datetime, timezone

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import AzureOpenAI
from pyspark.sql import functions as F


SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
SEARCH_INDEX = os.environ["AZURE_SEARCH_INDEX"]
SEARCH_KEY = os.environ["AZURE_SEARCH_KEY"]
AZURE_OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]
AZURE_OPENAI_API_KEY = os.environ["AZURE_OPENAI_API_KEY"]
AZURE_OPENAI_DEPLOYMENT = os.environ["AZURE_OPENAI_DEPLOYMENT"]

search_client = SearchClient(
    endpoint=SEARCH_ENDPOINT,
    index_name=SEARCH_INDEX,
    credential=AzureKeyCredential(SEARCH_KEY),
)
llm = AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
)

SYSTEM_PROMPT = """
You are the Apex Industrial Manufacturing maintenance decision-support assistant.
Use only the supplied retrieved knowledge and structured operational context.
Every operational claim must be supported by retrieved evidence or structured context.
Never invent a procedure, safety limit, work-order authorization, isolation approval,
or machine-control command. Never recommend bypassing a guard, interlock, alarm or
approved safety procedure. When evidence is insufficient, return INSUFFICIENT_EVIDENCE.
High or critical ML failure risk is a reason for human Reliability/Maintenance review,
not automatic machine action.
Return JSON with answer, answer_status, citations, recommended_next_steps and safety_notes.
"""

MODEL_FEATURES_FOR_QUERY = ["question"]


def embed_question(question):
    frame = spark.createDataFrame([(question,)], ["question"])
    embedded = frame.ai.embed(input_col="question", output_col="embedding")
    return embedded.select("embedding").first()["embedding"]


def retrieve(question, machine_type=None, top_k=5):
    vector = embed_question(question)
    vector_query = VectorizedQuery(
        vector=vector,
        k_nearest_neighbors=top_k,
        fields="embedding",
    )
    filters = ["active eq true"]
    if machine_type:
        filters.append(f"machine_type_code eq '{machine_type}' or machine_type_code eq null")
    search_filter = " and ".join(filters)

    results = search_client.search(
        search_text=question,
        vector_queries=[vector_query],
        query_type="semantic",
        semantic_configuration_name="industrial-iot-semantic",
        filter=search_filter,
        top=top_k,
        select=[
            "chunk_id", "document_id", "document_version", "title",
            "heading_path", "chunk_text", "source_locator",
        ],
    )

    docs = []
    for item in results:
        docs.append({
            "chunk_id": item.get("chunk_id"),
            "document_id": item.get("document_id"),
            "document_version": item.get("document_version"),
            "title": item.get("title"),
            "heading_path": item.get("heading_path"),
            "chunk_text": item.get("chunk_text"),
            "source_locator": item.get("source_locator"),
        })
    return docs


def load_machine_context(machine_id):
    if not machine_id:
        return None
    return (
        spark.table("mart.v_genai_machine_context_latest")
        .where(F.col("machine_id") == F.lit(machine_id))
        .limit(1)
        .collect()
    )[0].asDict() if spark.table("mart.v_genai_machine_context_latest")
        .where(F.col("machine_id") == F.lit(machine_id))
        .limit(1)
        .count() else None


def load_incidents(machine_id):
    if not machine_id:
        return []
    return [
        row.asDict()
        for row in (
            spark.table("mart.v_genai_incident_context")
            .where(F.col("machine_id") == F.lit(machine_id))
            .orderBy(F.col("event_time_utc").desc())
            .limit(10)
            .collect()
        )
    ]


def answer(question, machine_id=None, machine_type=None):
    retrieved = retrieve(question, machine_type=machine_type)
    structured = load_machine_context(machine_id)
    incidents = load_incidents(machine_id)

    evidence = {
        "retrieved_knowledge": retrieved,
        "machine_context": structured,
        "recent_incidents": incidents,
    }
    prompt = (
        "Question:\n" + question +
        "\n\nEvidence JSON:\n" + json.dumps(evidence, default=str) +
        "\n\nReturn valid JSON only. Citation objects must use chunk_id, document_id, "
        "document_version and source_locator from retrieved knowledge."
    )

    response = llm.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        temperature=0.1,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )

    parsed = json.loads(response.choices[0].message.content)
    return {
        "answer_id": "RAG-" + str(uuid.uuid4()),
        "question": question,
        "answer": parsed["answer"],
        "answer_status": parsed["answer_status"],
        "citations": parsed.get("citations", []),
        "recommended_next_steps": parsed.get("recommended_next_steps", []),
        "safety_notes": parsed.get("safety_notes", []),
        "used_structured_context": bool(structured or incidents),
        "retrieval_count": len(retrieved),
        "model_name": AZURE_OPENAI_DEPLOYMENT,
        "model_version": os.getenv("AZURE_OPENAI_API_VERSION"),
        "retrieval_query": question,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }


example = answer(
    os.getenv(
        "RAG_EXAMPLE_QUESTION",
        "What evidence should reliability review when a CNC shows rising vibration and temperature?",
    ),
    machine_id=os.getenv("RAG_EXAMPLE_MACHINE_ID"),
    machine_type=os.getenv("RAG_EXAMPLE_MACHINE_TYPE"),
)
print(json.dumps(example, indent=2, default=str))
