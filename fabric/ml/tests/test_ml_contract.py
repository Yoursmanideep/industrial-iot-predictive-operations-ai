from __future__ import annotations

import ast
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]


def test_ml_config_is_explicit_and_leakage_safe() -> None:
    cfg = yaml.safe_load((ROOT / "config/predictive_maintenance_ml.yaml").read_text())
    assert cfg["project"]["target_horizon_minutes"] == 60
    assert cfg["feature_engineering"]["snapshot_interval_minutes"] == 5
    assert "scenario_id" in cfg["feature_engineering"]["exclude_from_model"]
    assert cfg["model_registry"]["serving_flavor"] == "sklearn"


def test_ml_schemas_are_strict() -> None:
    for name in (
        "predictive_maintenance_features.schema.json",
        "predictive_maintenance_labels.schema.json",
        "predictive_maintenance_predictions.schema.json",
    ):
        schema = json.loads((ROOT / "schemas/ml" / name).read_text())
        assert schema["additionalProperties"] is False


def test_notebooks_are_valid_python() -> None:
    for name in (
        "04_ml_feature_engineering.py",
        "05_ml_train_register.py",
        "06_ml_batch_scoring.py",
    ):
        ast.parse((ROOT / "fabric/notebooks" / name).read_text())


def test_feature_engineering_has_causal_label_and_right_censor_controls() -> None:
    code = (ROOT / "fabric/notebooks/04_ml_feature_engineering.py").read_text()
    assert 'event_type") == "MachineFaulted"' in code
    assert "INTERVAL 60 MINUTES" in code
    assert "right_censored" in code
    assert "label_valid" in code


def test_training_has_temporal_split_mlflow_and_registry() -> None:
    code = (ROOT / "fabric/notebooks/05_ml_train_register.py").read_text()
    assert "chronological_split" in code
    assert "mlflow.set_experiment" in code
    assert "mlflow.sklearn.log_model" in code
    assert "mlflow.register_model" in code
    assert "RandomForestRegressor" in code
    assert "ExtraTreesRegressor" in code


def test_batch_scoring_uses_fabric_predict_transformer() -> None:
    code = (ROOT / "fabric/notebooks/06_ml_batch_scoring.py").read_text()
    assert "MLFlowTransformer" in code
    assert 'outputCol="prediction"' in code
    assert "modelName=MODEL_NAME" in code
    assert "modelVersion=int(MODEL_VERSION)" in code


def test_realtime_inference_is_secret_free_and_service_principal_based() -> None:
    contract = yaml.safe_load(
        (ROOT / "fabric/realtime/ml_inference_contract.yaml").read_text()
    )
    assert contract["orchestration"]["engine"] == "Dataflow_Gen2"
    assert contract["orchestration"]["authentication"]["method"] == "service_principal"
    assert contract["orchestration"]["secret_policy"]["hardcoded_credentials"] is False
