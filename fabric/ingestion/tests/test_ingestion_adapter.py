from __future__ import annotations

import json
from datetime import datetime, timezone

from fabric_ingest.adapter import FabricIngestionAdapter
from fabric_ingest.checkpoint import FileCheckpointStore
from fabric_ingest.identity import (
    canonical_batch_key,
    event_payload_hash,
    ingestion_batch_id,
)
from fabric_ingest.planner import FabricLoadPlanner
from fabric_ingest.source import ValidatedSourceScanner


ROOT_EVENT_1 = {
    "event_id": "EVT-11111111-1111-1111-1111-111111111111",
    "event_type": "MachineTelemetry",
    "schema_version": "1.0.0",
    "event_time": "2026-09-21T06:00:00+00:00",
    "ingestion_time": "2026-09-21T06:00:00.100000+00:00",
    "source_system": "simulator",
    "plant_id": "PLT-CHN-01",
    "line_id": "CHN-L01",
    "machine_id": "CHN-L01-CNC01",
    "machine_type": "CNC",
    "operating_state": "RUNNING",
    "spindle_rpm": 1000.0,
    "vibration_mm_s": 2.0,
    "temperature_c": 40.0,
    "pressure_bar": 100.0,
    "power_kw": 20.0,
    "production_rate_unit_min": 2.0,
    "quality_score_pct": 99.0,
    "feed_rate_mm_min": 100.0,
    "simulator_run_id": "RUN-22222222-2222-2222-2222-222222222222",
    "generation_sequence": 1,
    "generated_at_utc": "2026-09-21T06:00:00+00:00",
    "deterministic_seed": 20260921,
    "generator_version": "0.1.0",
    "configuration_version": "1.0.0",
}


def write_partition(root, event: dict) -> None:
    path = (
        root
        / "event_type=telemetry"
        / "event_date=2026-09-21"
        / "plant_id=PLT-CHN-01"
        / "telemetry.jsonl"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(event, separators=(",", ":"), sort_keys=True) + "\n", encoding="utf-8")


def test_batch_identity_is_portable_across_local_paths() -> None:
    key_a = canonical_batch_key(
        "RUN-22222222-2222-2222-2222-222222222222",
        "event_type=telemetry/event_date=2026-09-21/plant_id=PLT-CHN-01/telemetry.jsonl",
        "a" * 64,
        1,
        1,
        1,
    )
    key_b = canonical_batch_key(
        "RUN-22222222-2222-2222-2222-222222222222",
        "event_type=telemetry/event_date=2026-09-21/plant_id=PLT-CHN-01/telemetry.jsonl",
        "a" * 64,
        1,
        1,
        1,
    )
    assert key_a == key_b
    assert ingestion_batch_id(key_a).startswith("IBT-")


def test_scanner_discovers_partition_manifest(tmp_path) -> None:
    write_partition(tmp_path, ROOT_EVENT_1)
    manifests = ValidatedSourceScanner(tmp_path).discover()
    assert len(manifests) == 1
    manifest = manifests[0]
    assert manifest.event_type == "telemetry"
    assert manifest.event_date == "2026-09-21"
    assert manifest.plant_id == "PLT-CHN-01"
    assert manifest.event_count == 1
    assert manifest.first_generation_sequence == 1
    assert manifest.last_generation_sequence == 1
    assert manifest.ingestion_batch_id.startswith("IBT-")


def test_planner_includes_batch_id_in_immutable_destination(tmp_path) -> None:
    write_partition(tmp_path, ROOT_EVENT_1)
    manifest = ValidatedSourceScanner(tmp_path).discover()[0]
    plan = FabricLoadPlanner("Files/bronze").build(manifest)
    assert f"ingestion_batch_id={manifest.ingestion_batch_id}" in plan.one_lake_destination_path


def test_adapter_loads_then_skips_exact_replay(tmp_path) -> None:
    source = tmp_path / "source"
    write_partition(source, ROOT_EVENT_1)
    manifests = ValidatedSourceScanner(source).discover()

    store = FileCheckpointStore(tmp_path / "control.json")
    adapter = FabricIngestionAdapter(
        checkpoint_store=store,
        bronze_root=tmp_path / "bronze",
    )

    first = adapter.ingest(manifests[0])
    second = adapter.ingest(manifests[0])

    assert first.status == "COMPLETED"
    assert first.accepted_event_count == 1
    assert second.status == "SKIPPED_DUPLICATE"
    assert second.duplicate_event_count == 1
    assert second.destination_path == first.destination_path


def test_adapter_detects_conflicting_event_payload(tmp_path) -> None:
    source_a = tmp_path / "source-a"
    source_b = tmp_path / "source-b"
    write_partition(source_a, ROOT_EVENT_1)

    changed = dict(ROOT_EVENT_1)
    changed["temperature_c"] = 90.0
    write_partition(source_b, changed)

    store = FileCheckpointStore(tmp_path / "control.json")
    adapter = FabricIngestionAdapter(
        checkpoint_store=store,
        bronze_root=tmp_path / "bronze",
    )

    first_manifest = ValidatedSourceScanner(source_a).discover()[0]
    second_manifest = ValidatedSourceScanner(source_b).discover()[0]

    first = adapter.ingest(first_manifest)
    second = adapter.ingest(second_manifest)

    assert first.status == "COMPLETED"
    assert second.status == "QUARANTINED"
    assert second.conflict_event_count == 1
    assert second.destination_path is None

    snapshot = store.snapshot()
    assert snapshot["events"][ROOT_EVENT_1["event_id"]] == event_payload_hash(ROOT_EVENT_1)
