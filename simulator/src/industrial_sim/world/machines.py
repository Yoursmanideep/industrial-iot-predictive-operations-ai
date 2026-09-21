from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from industrial_sim.domain.machine import Machine, MachineIdentity, MachineState


@dataclass(frozen=True)
class MachineRuntime:
    machine: Machine
    rated_capacity_units_min: float
    installation_date: date
    criticality: str


class MachineWorldLoader:
    """Load the governed 270-machine master into runtime machine state."""

    def __init__(self, machine_csv: str | Path) -> None:
        self.machine_csv = Path(machine_csv)

    def load(
        self,
        initial_state: MachineState = MachineState.RUNNING,
        initial_state_distribution: dict[str, float] | None = None,
        deterministic_seed: int = 20260921,
    ) -> dict[str, MachineRuntime]:
        if not self.machine_csv.is_file():
            raise FileNotFoundError(self.machine_csv)

        runtimes: dict[str, MachineRuntime] = {}
        with self.machine_csv.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                machine_id = row["machine_id"]
                line_id = machine_id.split("-", 2)[0] + "-" + machine_id.split("-", 2)[1]
                plant_code = line_id.split("-")[0]
                plant_id = f"PLT-{plant_code}-01"
                machine_type_map = {
                    "CNC": "CNC",
                    "HPR": "HYDRAULIC_PRESS",
                    "ROB": "INDUSTRIAL_ROBOT",
                    "CON": "CONVEYOR",
                    "CMP": "COMPRESSOR",
                    "FRN": "FURNACE",
                    "INS": "INSPECTION",
                    "PKG": "PACKAGING",
                    "PAL": "PALLETIZER",
                }
                machine_type = machine_type_map[row["machine_type_code"]]
                identity = MachineIdentity(
                    machine_id=machine_id,
                    plant_id=plant_id,
                    line_id=line_id,
                    machine_type=machine_type,
                )
                state = self._select_initial_state(
                    machine_id,
                    initial_state,
                    initial_state_distribution,
                    deterministic_seed,
                )
                machine = Machine(
                    identity=identity,
                    state=state,
                    state_since=None,
                )
                runtimes[machine_id] = MachineRuntime(
                    machine=machine,
                    rated_capacity_units_min=float(row["rated_capacity"]),
                    installation_date=date.fromisoformat(row["installation_date"]),
                    criticality=row["criticality"],
                )

    @staticmethod
    def _select_initial_state(
        machine_id: str,
        default_state: MachineState,
        distribution: dict[str, float] | None,
        seed: int,
    ) -> MachineState:
        if not distribution:
            return default_state
        if abs(sum(distribution.values()) - 1.0) > 1e-9:
            raise ValueError("Initial-state distribution must sum to 1.0")
        raw = f"{seed}|initial_state|{machine_id}".encode("utf-8")
        fraction = int.from_bytes(hashlib.sha256(raw).digest()[:8], "big") / float(2**64 - 1)
        cumulative = 0.0
        for state_name, probability in distribution.items():
            if probability < 0:
                raise ValueError("Initial-state probabilities cannot be negative")
            cumulative += probability
            if fraction <= cumulative:
                return MachineState(state_name)
        return MachineState(list(distribution)[-1])

        if len(runtimes) != 270:
            raise ValueError(f"Expected 270 machines, loaded {len(runtimes)}")
        return runtimes
