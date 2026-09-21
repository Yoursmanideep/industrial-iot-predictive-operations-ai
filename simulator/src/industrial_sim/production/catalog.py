from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from industrial_sim.domain.production import ProductDefinition


class ProductionCatalogError(ValueError):
    """Raised when production reference data is invalid."""


@dataclass(frozen=True)
class ProductionCatalog:
    products: dict[str, ProductDefinition]
    lines: tuple[str, ...]

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
            products[product_id] = ProductDefinition(
                product_id=product_id,
                product_family=row["product_family"],
                unit_of_measure=row["unit_of_measure"],
                standard_cycle_time_seconds=float(row["standard_cycle_time_seconds"]),
                standard_unit_cost_inr=float(row["standard_unit_cost_inr"]),
                route=tuple(entry["route"]),
                quality_baseline_pct=float(entry["quality_baseline_pct"]),
                workload_factor=float(entry["workload_factor"]),
            )

    lines: list[str] = []
    with Path(line_csv).open("r", encoding="utf-8", newline="") as handle:
        lines.extend(row["line_id"] for row in csv.DictReader(handle))
    if len(lines) != 15 or len(set(lines)) != 15:
        raise ProductionCatalogError("Expected 15 unique production lines")
    return ProductionCatalog(products=products, lines=tuple(lines))