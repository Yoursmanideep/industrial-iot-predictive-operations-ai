# GenAI/RAG Deployment Boundary

Required deployment resources:

1. Microsoft Fabric workspace and Lakehouse.
2. Fabric AI Functions enabled for the target capacity/tenant.
3. Azure AI Search service with a vector-enabled index matching fabric/rag/azure_ai_search_index.yaml.
4. LLM endpoint for generation. The assistant notebook uses an Azure OpenAI-compatible deployment.
5. Connection references or secret storage for search and LLM credentials.

The repository contains no API keys or secrets.

Deployment order:

- copy data_reference/knowledge_base into Lakehouse Files/knowledge_base;
- copy the RAG benchmark into Files/rag_eval;
- run 08_rag_knowledge_ingestion.py;
- build or refresh the Azure AI Search index;
- run 09_rag_incident_assistant.py as the conversational service/test harness;
- run 10_rag_evaluate.py and persist benchmark results.

Plant-scoped structured context must be filtered before prompt construction. Knowledge visibility metadata must also be enforced during retrieval.

The assistant is decision support only. Machine-control and maintenance-authorization operations are intentionally excluded.
