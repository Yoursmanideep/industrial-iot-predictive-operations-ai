from uuid import UUID

from industrial_sim.lineage.identity import deterministic_event_id, run_namespace


def test_run_namespace_is_deterministic() -> None:
    run_id = UUID("12345678-1234-5678-1234-567812345678")
    assert run_namespace(run_id) == run_namespace(run_id)


def test_event_identity_is_deterministic() -> None:
    run_id = UUID("12345678-1234-5678-1234-567812345678")
    first = deterministic_event_id(
        run_id, "CHN-L01-CNC01", "MachineStarted",
        "2026-09-21T06:00:00+00:00", 1
    )
    second = deterministic_event_id(
        run_id, "CHN-L01-CNC01", "MachineStarted",
        "2026-09-21T06:00:00+00:00", 1
    )
    assert first == second


def test_event_identity_changes_with_sequence() -> None:
    run_id = UUID("12345678-1234-5678-1234-567812345678")
    first = deterministic_event_id(
        run_id, "CHN-L01-CNC01", "MachineStarted",
        "2026-09-21T06:00:00+00:00", 1
    )
    second = deterministic_event_id(
        run_id, "CHN-L01-CNC01", "MachineStarted",
        "2026-09-21T06:00:00+00:00", 2
    )
    assert first != second
