# 01 — Enterprise Foundation

## Purpose

This document locks the foundational scope used by every subsequent implementation artifact.

## Enterprise

**Apex Industrial Manufacturing**

The platform models a multi-plant industrial manufacturing enterprise with production, maintenance, quality, workforce, asset and contextual data domains.

## Scale

| Level | Scope |
|---|---:|
| Plants | 3 |
| Lines per plant | 5 |
| Machines per line | 18 |
| Total machines | 270 |

## Plant hierarchy

```
Enterprise
  └── Plant
       └── Production Area
            └── Production Line
                 └── Machine
                      └── Sensor / Signal
```

Plants:

- `PLT-CHN-01` — Chennai Manufacturing Plant
- `PLT-PUN-01` — Pune Manufacturing Plant
- `PLT-CBE-01` — Coimbatore Manufacturing Plant

Each plant has five production lines and each line contains 18 machines.

## Machine mix per production line

| Machine type | Code | Count |
|---|---|---:|
| CNC | CNC | 4 |
| Hydraulic Press | HPR | 2 |
| Industrial Robot | ROB | 3 |
| Conveyor | CON | 3 |
| Compressor | CMP | 2 |
| Furnace | FRN | 1 |
| Inspection | INS | 1 |
| Packaging | PKG | 1 |
| Palletizer | PAL | 1 |
| **Total** | | **18** |

## Operating shifts

| Shift | Local time |
|---|---|
| SH1 | 06:00–14:00 |
| SH2 | 14:00–22:00 |
| SH3 | 22:00–06:00 |

Timezone: `Asia/Kolkata`.

## Machine operating states

```
RUNNING
IDLE
SETUP
STARVED
BLOCKED
FAULT
MAINTENANCE
OFFLINE
RECOVERY
```

## Failure taxonomy

Failure modes are grouped into:

- Mechanical
- Thermal
- Pressure
- Electrical
- Process
- Control
- Environmental

Each failure mode defines its category, human-readable meaning and primary telemetry signals.

## Naming conventions

### Plant

`PLT-{CITY_CODE}-01`

### Area

`{CITY_CODE}-PA{NN}`

### Line

`{CITY_CODE}-L{NN}`

### Machine

`{CITY_CODE}-{LINE_CODE}-{TYPE_CODE}{NN}`

Examples:

- `CHN-L01-CNC01`
- `PUN-L03-ROB02`
- `CBE-L05-CMP01`

### Event

Events will use immutable event IDs and explicit event types. Event schemas will be defined in Stage 2.

## Engineering invariants

1. Every machine belongs to exactly one line at a point in time.
2. Every line belongs to exactly one plant.
3. Every machine has exactly one machine type.
4. Machine IDs are immutable.
5. Event IDs are unique.
6. Event time and ingestion time are separate concepts.
7. Historical changes to governed master data must be traceable.
8. The simulator must generate correlated behavior rather than independent random values.
9. Reprocessing an event batch must be idempotent.
10. No production secrets are stored in Git.

## Stage boundary

This stage defines enterprise identity, scale, hierarchy, machine catalog and failure taxonomy.

The next stage defines formal data contracts for telemetry, machine events, production, quality and maintenance.
