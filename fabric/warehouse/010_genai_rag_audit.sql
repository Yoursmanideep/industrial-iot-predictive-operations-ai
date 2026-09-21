-- Stage 3.18 — GenAI/RAG audit and evaluation surfaces

CREATE TABLE gold.fact_rag_answer_audit (
    rag_answer_fact_key BIGINT IDENTITY,
    answer_id VARCHAR(50) NOT NULL,
    question VARCHAR(2000) NOT NULL,
    answer_status VARCHAR(40) NOT NULL,
    retrieval_count INT NOT NULL,
    used_structured_context BIT NOT NULL,
    model_name VARCHAR(150) NULL,
    model_version VARCHAR(80) NULL,
    generated_at_utc DATETIME2(3) NOT NULL,
    plant_sk BIGINT NULL,
    machine_sk BIGINT NULL
);

GO

CREATE TABLE gold.fact_rag_evaluation (
    rag_evaluation_fact_key BIGINT IDENTITY,
    question_id VARCHAR(50) NOT NULL,
    question VARCHAR(2000) NOT NULL,
    category VARCHAR(80) NOT NULL,
    retrieval_score DECIMAL(9,6) NULL,
    citation_document_match BIT NULL,
    citation_chunk_match BIT NULL,
    groundedness DECIMAL(9,4) NULL,
    relevance DECIMAL(9,4) NULL,
    answer_completeness DECIMAL(9,4) NULL,
    answer_status VARCHAR(40) NULL,
    evaluated_at_utc DATETIME2(3) NOT NULL
);

GO

CREATE VIEW mart.v_rag_answer_audit
AS
SELECT
    answer_id,
    answer_status,
    retrieval_count,
    used_structured_context,
    model_name,
    model_version,
    generated_at_utc,
    plant_sk,
    machine_sk
FROM gold.fact_rag_answer_audit;

GO

CREATE VIEW mart.v_rag_evaluation_health
AS
SELECT
    category,
    COUNT(*) AS evaluation_cases,
    AVG(retrieval_score) AS avg_retrieval_score,
    AVG(groundedness) AS avg_groundedness,
    AVG(relevance) AS avg_relevance,
    AVG(answer_completeness) AS avg_answer_completeness
FROM gold.fact_rag_evaluation
GROUP BY category;
