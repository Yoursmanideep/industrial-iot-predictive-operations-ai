# 10 — Seed Reference Data

## Purpose

Stage 3.2 provides deterministic seed data for the physical master-data model.

The seed layer is generated from the locked Stage 1 machine inventory and Stage 2 governed reference definitions. It is designed to make downstream simulator behavior reproducible.

## Seed counts

| Dataset | Records |
|---|---:|
| Machine inventory | 270 |
| Machine master | 270 |
| Machine models | 18 |
| Products | 12 |
| Operators | 60 |
| Technicians | 36 |
| Suppliers | 18 |
| Spare parts | 36 |
| Failure modes | 25 |
| Alarm codes | 6 |
| Production reasons | 12 |
| Quality defects | 7 |

## Machine master

The 270 physical machines are derived from the existing Stage 1 inventory. Each machine receives:

- surrogate key
- model reference
- serial number
- installation date
- rated capacity
- capacity unit
- operating temperature envelope
- criticality
- lifecycle status
- effective dating

The machine's identity, plant, line, production area and type remain consistent with the Stage 1 inventory.

## Machine models

There are two deterministic model variants for each of the nine machine types.

```text
CNC              → CNC-M01 / CNC-M02
Hydraulic Press  → HPR-M01 / HPR-M02
Robot            → ROB-M01 / ROB-M02
Conveyor         → CON-M01 / CON-M02
Compressor       → CMP-M01 / CMP-M02
Furnace          → FRN-M01 / FRN-M02
Inspection       → INS-M01 / INS-M02
Packaging        → PKG-M01 / PKG-M02
Palletizer       → PAL-M01 / PAL-M02
```

## Products

Twelve reference products represent the manufacturing portfolio. Standard cycle time and standard unit cost are reference characteristics, not actual transactional measurements.

## Workforce

Each plant has:

- 20 production operators
- 12 maintenance technicians

Operators and technicians use separate identity spaces because their operational roles differ.

## Suppliers and spare parts

Eighteen suppliers represent OEMs, authorized distributors, local vendors, raw-material suppliers and utility providers.

Thirty-six spare parts cover bearings, sensors, motors, belts, hydraulic components, thermal components, electrical parts, lubricants and other maintenance materials.

Each spare part has one primary supplier in the seed model.

## Governed references

Seeded controlled tables:

```text
ref.failure_mode
ref.alarm_code
ref.production_reason
ref.quality_defect
```

Failure modes align with the Stage 1 taxonomy.

Alarm codes are shared definitions. `machine_type_code = ALL` means the alarm concept is globally governed; actual signal applicability remains constrained by the machine telemetry profile.

## Determinism

The seed data does not rely on runtime random number generation.

Given the same Stage 1 inventory and definition files, the seed records are reproducible.

This is important because the simulator will later need deterministic baseline scenarios for testing and model-training experiments.

## Validation expectations

Stage 3.2 seed validation must confirm:

- expected row counts
- unique business keys
- machine/model type consistency
- machine hierarchy consistency
- spare-part/supplier references
- valid controlled failure codes
- valid controlled alarm codes
- valid production reasons
- valid quality defect codes
- exactly one current SCD row per business key
- no negative costs, quantities or lead times

## Stage boundary

Stage 3.2 creates reusable seed data only.

Large historical fact data and continuous telemetry are not generated here.

The next stage will be the **physical event seed model and simulator scenario design**, where we define how orders, batches, machine states, failures and maintenance episodes are orchestrated over simulated time.