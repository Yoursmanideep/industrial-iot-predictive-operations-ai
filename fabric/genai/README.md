# GenAI / RAG Intelligence Layer

Stage 3.18 adds a grounded maintenance knowledge and conversational decision-support layer.

Architecture:

Versioned manuals, SOPs and playbooks
|
v
Fabric Lakehouse Files
|
v
Fabric Spark chunking
|
v
Fabric AI Functions embeddings
|
v
Azure AI Search hybrid/vector retrieval
|
+----------------------+
|                      |
v                      v
Structured Gold      Retrieved knowledge
context              |
|                    |
+----------+---------+
           v
    grounded LLM answer
           |
       citations +
       safety notes
           |
           v
 Power BI / Power Apps / operations

The assistant is advisory. It does not authorize maintenance, certify isolation, bypass safeguards or issue machine-control commands.

Fabric AI Functions provide embeddings and response generation. Azure AI Search is used as the vector/hybrid retrieval layer following the current Fabric RAG implementation pattern.
