from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from industrial_sim.config.loader import load_generation_contract
from industrial_sim.domain.run import RunMode
from industrial_sim.engine.run_engine import RunEngine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="industrial-sim",
        description="Deterministic industrial IoT simulation foundation.",
    )
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path("../config/simulator_data_generation.yaml"),
        help="Path to the Stage 3.4 generation contract.",
    )
    parser.add_argument(
        "--mode",
        choices=[mode.value for mode in RunMode],
        default=RunMode.LIVE.value,
    )
    parser.add_argument(
        "--seconds",
        type=int,
        default=15,
        help="Simulation duration for the foundation smoke run.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.seconds <= 0:
        raise SystemExit("--seconds must be greater than zero.")

    contract = load_generation_contract(args.contract)
    start = datetime.now(timezone.utc)
    end = start + timedelta(seconds=args.seconds)

    engine = RunEngine(contract)
    run, context, clock = engine.create_run(
        mode=RunMode(args.mode),
        start_time=start,
        end_time=end,
    )

    tick_count = 0
    while RunEngine.tick(context, clock, end):
        tick_count += 1

    print(f"simulator_run_id={run.simulator_run_id}")
    print(f"run_mode={run.run_mode.value}")
    print(f"deterministic_seed={run.deterministic_seed}")
    print(f"ticks={tick_count}")
    print(f"final_simulation_time={context.now_utc().isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
