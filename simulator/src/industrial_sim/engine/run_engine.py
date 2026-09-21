from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from industrial_sim.config.loader import GenerationContract
from industrial_sim.domain.run import RunMode, RunStatus, SimulationRun
from industrial_sim.engine.clock import SimulationClock
from industrial_sim.engine.context import SimulationContext


@dataclass
class RunEngine:
    """Create and advance deterministic simulation run state."""

    generation_contract: GenerationContract
    generator_version: str = "0.1.0"

    def create_run(
        self,
        mode: RunMode,
        start_time: datetime,
        end_time: datetime,
        seed: int | None = None,
        source_run_id: UUID | None = None,
        configuration_version: str | None = None,
    ) -> tuple[SimulationRun, SimulationContext, SimulationClock]:
        effective_seed = (
            self.generation_contract.default_seed if seed is None else seed
        )
        effective_config = (
            self.generation_contract.contract_version
            if configuration_version is None
            else configuration_version
        )
        run_id = uuid4()

        run = SimulationRun(
            simulator_run_id=run_id,
            run_mode=mode,
            generator_version=self.generator_version,
            configuration_version=effective_config,
            deterministic_seed=effective_seed,
            simulation_start_time=start_time,
            simulation_end_time=end_time,
            source_run_id=source_run_id,
            status=RunStatus.RUNNING,
        )
        context = SimulationContext(
            simulator_run_id=run_id,
            deterministic_seed=effective_seed,
            generator_version=self.generator_version,
            configuration_version=effective_config,
            current_time=start_time,
        )
        clock = SimulationClock(
            current_time=start_time,
            tick_seconds=int(self.generation_contract.raw["time"]["live_tick_seconds"]),
        )
        return run, context, clock

    @staticmethod
    def tick(
        context: SimulationContext,
        clock: SimulationClock,
        end_time: datetime,
    ) -> bool:
        """Advance one tick; return False when the run reaches its end."""
        if clock.current_time >= end_time:
            return False
        clock.tick()
        context.current_time = clock.current_time
        return context.current_time <= end_time
