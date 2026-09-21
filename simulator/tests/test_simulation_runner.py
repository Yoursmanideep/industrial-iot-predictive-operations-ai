from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from industrial_sim.domain.run import RunMode
from industrial_sim.simulation.output import PartitionedEventStreamWriter
from industrial_sim.simulation.runner import EnterpriseSimulationRunner
from industrial_sim.world.machines import MachineWorldLoader

ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT / "data_reference" / "seed"
RUN_ID = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
START = datetime(2026, 9, 21, 0, 0, tzinfo=timezone.utc)


def test_bootstrap_machine_distribution_is_deterministic() -> None:
    distribution = {
        "RUNNING": 0.80,
        "IDLE": 0.08,
        "SETUP": 0.04,
        "MAINTENANCE": 0.03,
        "OFFLINE": 0.05,
    }
    loader = MachineWorldLoader(DATA_ROOT / "machine_master_seed.csv")
    first = loader.load(
        initial_state_distribution=distribution,
        deterministic_seed=20260921,
    )
    second = loader.load(
        initial_state_distribution=distribution,
        deterministic_seed=20260921,
    )
    states_a = {
        machine_id: runtime.machine.state.value
        for machine_id, runtime in first.items()
    }
    states_b = {
        machine_id: runtime.machine.state.value
        for machine_id, runtime in second.items()
    }
    assert states_a == states_b
    assert len(states_a) == 270


def test_stream_writer_appends_across_multiple_write_calls(tmp_path: Path) -> None:
    from industrial_sim.telemetry.events import MachineTelemetryEvent

    def event(seq: int) -> MachineTelemetryEvent:
        return MachineTelemetryEvent(
            event_id=f"EVT-{seq:032x}"[:40],
            event_type="MachineTelemetry",
            schema_version="1.0.0",
            event_time=START + timedelta(seconds=seq),
            ingestion_time=START + timedelta(seconds=seq, milliseconds=100),
            source_system="simulator",
            plant_id="PLT-CHN-01",
            line_id="CHN-L01",
            machine_id="CHN-L01-CNC01",
            machine_type="CNC",
            operating_state="RUNNING",
            signals={
                "spindle_rpm": 1000.0,
                "vibration_mm_s": 2.0,
                "temperature_c": 40.0,
                "pressure_bar": 100.0,
                "power_kw": 20.0,
                "feed_rate_mm_min": 100.0,
                "production_rate_unit_min": 1.0,
                "quality_score_pct": 99.0,
            },
            generation_sequence=seq,
        )

    writer = PartitionedEventStreamWriter(tmp_path)
    writer.write([event(1)])
    writer.write([event(2)])
    writer.close()

    files = list(tmp_path.rglob("*.jsonl"))
    assert len(files) == 1
    assert len(files[0].read_text(encoding="utf-8").splitlines()) == 2


def test_runner_uses_deterministic_default_run_id(tmp_path: Path) -> None:
    runner = EnterpriseSimulationRunner(ROOT)
    result_a = runner.run(
        mode=RunMode.LIVE,
        start_time=START,
        end_time=START + timedelta(seconds=5),
        seed=20260921,
        run_id=None,
        output_root=tmp_path / "runner-a",
    )
    result_b = runner.run(
        mode=RunMode.LIVE,
        start_time=START,
        end_time=START + timedelta(seconds=5),
        seed=20260921,
        run_id=None,
        output_root=tmp_path / "runner-b",
    )
    assert result_a.run_id == result_b.run_id
    assert result_a.mode is RunMode.LIVE
    assert result_a.simulation_end > result_a.simulation_start
