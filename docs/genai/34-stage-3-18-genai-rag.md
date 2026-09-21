# 34 — GenAI and RAG Intelligence

## Scope

Stage 3.18 adds a governed Retrieval-Augmented Generation layer for Apex Industrial Manufacturing.

The assistant combines:

1. versioned maintenance manuals, SOPs, alarm playbooks, failure-mode guides and safety procedures;
2. current structured machine, incident, production and predictive-maintenance context from Fabric Gold and real-time surfaces.

The answer is required to remain grounded in those evidence sources.

## Knowledge lifecycle

Repository knowledge documents are copied into Lakehouse Files during deployment.

The Fabric ingestion notebook creates governed knowledge chunks and embeddings. Azure AI Search provides hybrid retrieval with vector search, lexical search and semantic ranking.

Each chunk preserves document ID, version, knowledge domain, machine type, heading path, source locator, active status and visibility scope.

## Structured operational context

The Warehouse exposes:

- mart.v_genai_machine_context_latest
- mart.v_genai_incident_context
- mart.v_genai_production_context
- mart.v_genai_maintenance_context

The assistant can combine these with the Stage 3.16/3.17 predictive-maintenance risk context.

A predictive score is evidence, not a diagnosis. The assistant must distinguish prediction from observed failure.

## Answer contract

Every response contains:

- answer status
- grounded answer
- citations
- recommended next steps
- safety notes
- structured-context usage flag
- retrieval count
- model metadata and timestamp

When evidence is insufficient, the response uses INSUFFICIENT_EVIDENCE rather than inventing an explanation.

## Safety and governance

The assistant cannot:

- issue machine-control commands;
- authorize maintenance;
- certify lockout/tagout;
- approve return-to-service;
- bypass guards, interlocks or alarms;
- invent safety limits.

High and critical predictive-maintenance risk is routed to human Reliability/Maintenance review.

## Evaluation

The benchmark separates retrieval from answer quality.

Deterministic checks:

- top-N document retrieval;
- citation document matching;
- citation chunk matching.

AI-assisted checks:

- groundedness;
- relevance;
- completeness.

Results are persisted so retrieval, prompt and model changes can be compared for regression.

## Current Microsoft Fabric alignment

Microsoft's current Fabric RAG quickstart uses chunking, embeddings and Azure AI Search for vector retrieval. Fabric AI Functions provide ai.embed and ai.generate_response capabilities across notebooks and other Fabric experiences.

Microsoft's current RAG evaluation tutorial separates retrieval evaluation from answer groundedness/relevance evaluation and saves evaluation results for comparison.

References:
https://learn.microsoft.com/en-us/fabric/data-science/quickstart-building-retrieval-augmented-generation
https://learn.microsoft.com/en-us/fabric/data-science/ai-functions/overview
https://learn.microsoft.com/en-us/fabric/data-science/tutorial-evaluate-rag-performance

## Runtime boundary

Source-controlled Stage 3.18 artifacts are complete.

Actual vector-index creation, embeddings, retrieval results, LLM responses and evaluation scores require deployed Fabric/Azure resources and credentials.

No live GenAI result is claimed from Git alone.
