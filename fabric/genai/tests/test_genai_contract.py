from __future__ import annotations

import ast
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_rag_config_is_grounded_and_safe() -> None:
    cfg = yaml.safe_load((ROOT.parent / "config/genai_rag.yaml").read_text())
    assert cfg["rag"]["retrieval"]["citation_required"] is True
    assert cfg["rag"]["answer_policy"]["ground_only_in_retrieved_evidence"] is True
    assert cfg["rag"]["answer_policy"]["automatic_machine_control"] is False
    assert cfg["rag"]["answer_policy"]["automatic_work_order_creation"] is False


def test_genai_schemas_are_strict() -> None:
    for name in ("knowledge_chunk.schema.json", "rag_answer.schema.json"):
        schema = json.loads((ROOT.parent / "schemas/genai" / name).read_text())
        assert schema["additionalProperties"] is False


def test_rag_notebooks_parse() -> None:
    for name in (
        "08_rag_knowledge_ingestion.py",
        "09_rag_incident_assistant.py",
        "10_rag_evaluate.py",
    ):
        ast.parse((ROOT / "notebooks" / name).read_text())


def test_rag_assets_exist() -> None:
    assert (ROOT / "rag/azure_ai_search_index.yaml").is_file()
    assert (ROOT / "rag/prompt_contract.yaml").is_file()
    assert (ROOT / "rag/rag_evaluation.yaml").is_file()
    assert (ROOT / "warehouse/009_genai_operational_context.sql").is_file()
    assert (ROOT / "warehouse/010_genai_rag_audit.sql").is_file()


def test_rag_pipeline_forbids_unsafe_automation() -> None:
    cfg = yaml.safe_load((ROOT / "pipelines/06_genai_rag_contract.yaml").read_text())
    assert cfg["quality_gates"]["no_machine_control_actions"] is True
    assert cfg["quality_gates"]["no_maintenance_authorization"] is True


def test_benchmark_has_multiple_grounding_categories() -> None:
    benchmark = (ROOT.parent / "data_reference/rag_eval/rag_eval_questions.jsonl").read_text().splitlines()
    assert len(benchmark) == 12
    categories = {json.loads(row)["category"] for row in benchmark}
    assert {"known_failure_mode", "safety_boundary", "structured_context_plus_manual"} <= categories
