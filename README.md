# Industrial IoT Predictive Operations & AI Intelligence Platform

Enterprise-grade Industrial IoT, analytics, AI/ML and operational intelligence platform built on Microsoft Fabric.

## Stage 1 — Enterprise Foundation

- Enterprise: Apex Industrial Manufacturing
- Plants: 3
- Lines per plant: 5
- Machines per line: 18
- Total machines: 270

The project is designed around meaningful engineering complexity across real-time data engineering, SQL/database engineering, analytics, ML/AI, GenAI/RAG, security, governance, Power BI, operational workflows and GitHub-based engineering practices.

## Repository structure

- config/ — enterprise configuration and controlled vocabularies
- data_reference/ — reference datasets
- docs/ — architecture, data-engineering, simulator, real-time and ML documentation
- schemas/ — canonical data, ingestion and ML contracts
- simulator/ — deterministic industrial IoT simulator
- fabric/ — Microsoft Fabric ingestion, Silver, Gold, real-time and ML engineering artifacts
- powerbi/ — source-controlled semantic model and report artifacts

## Engineering principle

Every component must have a defined business or engineering purpose. Avoid technology for technology's sake.

## Current progression

Stage 3.5–3.9 established the deterministic simulator, synchronized execution, enterprise runner and validation/quarantine boundary.

Stage 3.10 established replay-safe Fabric ingestion into Bronze.
Stage 3.11 established Bronze-to-Silver normalization, deduplication, SCD2 master validation and Silver quality auditing.
Stage 3.12 established the SQL-first Fabric Warehouse Gold layer, conformed star-schema dimensions, production/downtime facts, OEE calculations and Power BI mart views.
Stage 3.13 established the Power BI semantic model, Direct Lake TMDL definition, KPI measures, dynamic plant RLS and report blueprint.
Stage 3.14 established the source-controlled PBIP/PBIR report project with executive, plant, machine-health, reliability, production/quality and drill-through reporting pages.
Stage 3.15 established the real-time Eventstream/Eventhouse/Activator path, KQL operational monitoring, Power Automate workflows and the optional simulator-to-Eventstream live bridge.
Stage 3.16 establishes the predictive-maintenance ML lifecycle: 5-minute features, causal 60-minute failure labels, chronological validation, MLflow experiment/model registration, Fabric PREDICT batch scoring, Warehouse prediction persistence and preview real-time model-endpoint integration.
Stage 3.17 establishes ML operationalization: prediction-driven maintenance review workflows, model performance and feature-drift monitoring, model explainability, Power BI risk/health surfaces and governed Activator actions.

Stage 3.18 establishes the GenAI/RAG intelligence layer: versioned maintenance knowledge, Fabric embeddings, Azure AI Search retrieval, grounded answers with citations, structured operational context and repeatable RAG evaluation.
