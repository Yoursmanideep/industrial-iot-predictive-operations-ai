from __future__ import annotations

import ast
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_monitoring_config_is_governed() -> None:
    cfg = yaml.safe_load((ROOT.parent / "config/ml_operational_monitoring.yaml").read_text())
    assert cfg["monitoring"]["model_name"]
    assert cfg["monitoring"]["thresholds"]["psi_critical"] > cfg["monitoring"]["thresholds"]["psi_warn"]
    assert cfg["governance"]["no_auto_promotion_on_drift"] is True
    assert cfg["governance"]["no_auto_retraining_without_review"] is True


def test_monitoring_notebook_is_valid_python() -> None:
    source = (ROOT / "notebooks/07_ml_monitoring_explainability.py").read_text()
    ast.parse(source)
    assert "feature_importances_" in source
    assert "right_censor" not in source


def test_operationalization_pipeline_has_monitoring_and_drift_outputs() -> None:
    cfg = yaml.safe_load((ROOT / "pipelines/05_ml_operationalization_contract.yaml").read_text())
    activity_names = [a["name"] for a in cfg["activities"]]
    assert "MonitorAndExplainModel" in activity_names
    assert "PersistFeatureDrift" in activity_names
    assert cfg["quality_gates"]["no_auto_model_promotion_on_monitoring_breach"] is True


def test_activator_rules_do_not_auto_stop_or_promote() -> None:
    cfg = yaml.safe_load((ROOT.parent / "config/activator_ml_rules.yaml").read_text())
    assert len(cfg["rules"]) == 3
    assert cfg["governance"]["automatic_machine_stop"] is False
    assert cfg["governance"]["automatic_model_promotion"] is False


def test_power_automate_reviews_are_human_governed() -> None:
    review = (ROOT / "power_automate/05_predictive_maintenance_review.yaml").read_text()
    health = (ROOT / "power_automate/06_ml_model_health_review.yaml").read_text()
    assert "human_review_required: true" in review
    assert "automatic_model_promotion: false" in review
    assert "human_review_required: true" in health
    assert "automatic_retraining: false" in health
