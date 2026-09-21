from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from industrial_sim.domain.run import RunMode
from industrial_sim.simulation.runner import EnterpriseSimulationRunner
from industrial_sim.transport.eventstream import (
    EventHubEventstreamPublisher,
    EventstreamPublisherConfig,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="industrial-sim",
        description="Deterministic enterprise industrial IoT simulator.",
    )
    parser.add_argument(
        "--mode",
        choices=[mode.value for mode in RunMode],
        default=RunMode.LIVE.value,
        help="Simulation mode.",
    )
    parser.add_argument(
        "--start",
        help="UTC ISO-8601 simulation start time.",
    )
    parser.add_argument(
        "--end",
        help="UTC ISO-8601 simulation end time.",
    )
    parser.add_argument(
        "--minutes",
        type=int,
        default=5,
        help="Duration when --end is omitted.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Deterministic seed. Defaults to the governed contract seed.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional simulator run UUID.",
    )
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=None,
        help="Repository root. Defaults to the project root containing config/.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/simulator"),
        help="Output directory for streamed events and manifests.",
    )
    parser.add_argument(
        "--publish-eventstream",
        action="store_true",
        help="Publish validated events to the Fabric Eventstream Custom Endpoint.",
    )
    return parser


def _parse_utc(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("Simulation timestamps must include a timezone.")
    return parsed.astimezone(timezone.utc)


def main() -> int:
    args = build_parser().parse_args()
    if args.minutes <= 0:
        raise SystemExit("--minutes must be greater than zero.")

    repository_root = (
        args.repository_root.resolve()
        if args.repository_root is not None
        else Path(__file__).resolve().parents[4]
    )
    runner = EnterpriseSimulationRunner(repository_root)

    start = (
        _parse_utc(args.start)
        if args.start is not None
        else datetime.now(timezone.utc)
    )
    end = (
        _parse_utc(args.end)
        if args.end is not None
        else start + timedelta(minutes=args.minutes)
    )
    run_id = UUID(args.run_id) if args.run_id else None

    publisher = None
    if args.publish_eventstream:
        publisher = EventHubEventstreamPublisher(
            EventstreamPublisherConfig.from_environment()
        )

    result = runner.run(
        mode=RunMode(args.mode),
        start_time=start,
        end_time=end,
        seed=args.seed,
        run_id=run_id,
        output_root=args.output,
        event_publisher=publisher,
    )

    print(f"simulator_run_id=RUN-{result.run_id}")
    print(f"run_mode={result.mode.value}")
    print(f"deterministic_seed={runner.generation_contract.default_seed if args.seed is None else args.seed}")
    print(f"ticks={result.tick_count}")
    print(f"orders_registered={result.order_count}")
    print(f"events_emitted={result.event_count}")
    print(f"valid_events={result.valid_event_count}")
    print(f"quarantined_events={result.quarantined_event_count}")
    print(f"simulation_start={result.simulation_start.isoformat()}")
    print(f"simulation_end={result.simulation_end.isoformat()}")
    print(f"run_manifest={result.output_manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
