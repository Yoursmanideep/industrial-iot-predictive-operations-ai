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

- `config/` — enterprise configuration and controlled vocabularies
- `data_reference/` — reference datasets
- `docs/architecture/` — enterprise architecture decisions
- `schemas/` — canonical data and ingestion contracts
- `simulator/` — deterministic industrial IoT simulator
- `fabric/` — Microsoft Fabric ingestion, Bronze and Eventhouse engineering artifacts

## Engineering principle

Every component must have a defined business or engineering purpose. Avoid technology for technology's sake.

## Current progression

Stages 3.5–3.9 establish the deterministic simulator, synchronized execution, enterprise runner and validation/quarantine boundary.

Stage 3.10 establishes the Microsoft Fabric ingestion control plane.

## Current progression

Stage 3.10 established replay-safe Fabric ingestion into Bronze.
Stage 3.11 establishes Bronze-to-Silver normalization, deduplication, SCD2 master validation and Silver quality auditing.

Stage 3.12 establishes the SQL-first Fabric Warehouse Gold layer, conformed star-schema dimensions, production/downtime facts, OEE calculations and Power BI mart views.

Stage 3.13 establishes the Power BI semantic model, Direct Lake TMDL definition, KPI measures, dynamic plant RLS and report blueprint.
