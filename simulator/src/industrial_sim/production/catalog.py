from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from collections import defaultdict

import yaml

from industrial_sim.domain.production import ProductDefinition


class ProductionCatalogError(ValueError):
    """Raised when production reference data is invalid."""


@dataclass(frozen=True)
class ProductionCatalog:
    products: dict[str, ProductDefinition]
    lines: tuple[str, ...]
    machines_by_line_type: dict[str, dict[str, tuple[tuple[str, int], ...]]]

    def route_machine_ids(self, line_id: str, product_id: str) -> tuple[str, ...]:
        product = self.product(product_id)
        try:
            line_machines = self.machines_by_line_type[line_id]
        except KeyError as exc:
            raise ProductionCatalogError(f"Unknown line_id: {line_id}") from exc

        selected: list[str] = []
        for machine_type in product.route:
            machines = line_machines.get(machine_type, ())
            if not machines:
                raise ProductionCatalogError(
                    f"No {machine_type} machine available on {line_id}"
                )
            selected.append(machines[0][0])
        return tuple(selected)

    def product(self, product_id: str) -> ProductDefinition:
        try:
            return self.products[product_id]
        except KeyError as exc:
            raise ProductionCatalogError(f"Unknown product_id: {product_id}") from exc


def load_production_catalog(config_path: str | Path, product_csv: str | Path, line_csv: str | Path) -> ProductionCatalog:
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    if not isinstance(config, dict) or not isinstance(config.get("products"), dict):
        raise ProductionCatalogError("Production configuration must contain products")

    products: dict[str, ProductDefinition] = {}
    with Path(product_csv).open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            product_id = row["product_id"]
            entry: dict[str, Any] = config["products"].get(product_id)
            if entry is None:
                raise ProductionCatalogError(f"Missing route configuration for {product_id}")
            route = tuple(entry["route"])
            if not route:
                raise ProductionCatalogError(f"Route cannot be empty for {product_id}")
            products[product_id] = ProductDefinition(
                product_id=product_id,
                product_family=row["product_family"],
                unit_of_measure=row["unit_of_measure"],
                standard_cycle_time_seconds=float(row["standard_cycle_time_seconds"]),
                standard_unit_cost_inr=float(row["standard_unit_cost_inr"]),
                route=route,
                quality_baseline_pct=float(entry["quality_baseline_pct"]),
                workload_factor=float(entry["workload_factor"]),
            )

    lines: list[str] = []
    with Path(line_csv).open("r", encoding="utf-8", newline="") as handle:
        lines.extend(row["line_id"] for row in csv.DictReader(handle))
    if len(lines) != 15 or len(set(lines)) != 15:
        raise ProductionCatalogError("Expected 15 unique production lines")

    machines_by_line_type: dict[str, dict[str, tuple[tuple[str, int], ...]]] = {}
    machine_csv = Path(line_csv).parent / "machine_master_seed.csv"
    if not machine_csv.is_file():
        raise ProductionCatalogError(f"Machine master seed not found: {machine_csv}")
    grouped: dict[str, dict[str, list[tuple[str, int]]]] = defaultdict(lambda: defaultdict(list))
    with machine_csv.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            grouped[row["machine_id"].split("-")[0] + "-L" + row["machine_id"].split("-L")[1].split("-")[0]][row["machine_type_code"]].append(
                (row["machine_id"], int(row["machine_sequence"]))
            )
    for line_id in lines:
        line_groups = grouped.get(line_id, {})
        machines_by_line_type[line_id] = {
            machine_type: tuple(sorted(items, key=lambda item: (item[1], item[0])))
            for machine_type, items in line_groups.items()
        }
        if sum(len(items) for items in line_groups.values()) != 18:
            raise ProductionCatalogError(f"Line {line_id} must contain exactly 18 machines")

    for product_id, product in products.items():
        for line_id in lines:
            missing_types = [machine_type for machine_type in product.route if machine_type not in machines_by_line_type[line_id]]
            if missing_types:
                raise ProductionCatalogError(
                    f"Product {product_id} route is not executable on {line_id}: {missing_types}"
                )

    return ProductionCatalog(
        products=products,
        lines=tuple(lines),
        machines_by_line_type=machines_by_line_type,
    )