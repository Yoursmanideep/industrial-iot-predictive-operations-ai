# 02 — Global Data Standards

## Purpose

Stage 2.1 establishes the cross-domain data rules that apply to every contract in the platform. The purpose is to prevent inconsistent identifiers, timestamps, units, null semantics, event ordering and schema-version behavior across telemetry, production, quality, maintenance and AI/ML data.

## 1. Canonical time standard

The enterprise operates in **Asia/Kolkata**, but the platform's canonical persisted event timestamps are **UTC**.

Each operational event distinguishes:

- `event_time` — when the physical/business event occurred.
- `ingestion_time` — when the platform received the event.
- `processing_time` — when processing completed where applicable.

These timestamps must never be substituted for one another.

Primary ordering uses `event_time`; `event_id` is the tie-breaker.

Expected representation:

```
2026-09-21T05:16:23.145Z
```

Precision is milliseconds.

## 2. Naming standard

All data field, table and configuration-property names use:

```
snake_case
```

Controlled enumerations use:

```
UPPER_SNAKE_CASE
```

Event types use:

```
PascalCase
```

Identifiers contain no spaces.

## 3. Identifier standard

Identifiers are immutable.

Core identity keys include:

| Entity | Example |
|---|---|
| Plant | `PLT-CHN-01` |
| Production area | `CHN-PA01` |
| Line | `CHN-L01` |
| Machine | `CHN-L01-CNC01` |

Event and operational identifiers are globally unique:

- `EVT-{UUID}`
- `WO-{UUID}`
- `INC-{UUID}`

Machine, plant and line identifiers do not change during their lifecycle.

## 4. Measurement standard

Persist measurements in canonical units:

| Measurement | Canonical unit |
|---|---|
| Temperature | °C |
| Vibration | mm/s |
| Pressure | bar |
| Rotational speed | rpm |
| Power | kW |
| Current | A |
| Voltage | V |
| Force | kN |
| Torque | N·m |
| Distance | mm |
| Duration | s |
| Throughput | unit/min |
| Energy | kWh |

Any source-unit conversion must be explicit and traceable.

## 5. Null and missing-value semantics

`NULL` represents an unavailable or unpopulated value.

Do not use magic values such as:

```
-1
999999
"NA"
"UNKNOWN"
""
```

to represent missing data.

A value of zero is a valid measurement when the underlying measurement is actually zero.

Empty strings are not valid data values.

## 6. Controlled vocabularies

Enumerated values must come from governed reference vocabularies.

Examples include:

- machine operating states
- severity
- event types
- quality status
- data-quality status

Unknown enumeration values are not silently accepted. A vocabulary change must go through contract change control.

## 7. Common event envelope

All domain events will share a common envelope containing:

```
event_id
event_type
schema_version
event_time
ingestion_time
source_system
```

Where relevant, events also carry:

```
correlation_id
causation_id
plant_id
line_id
machine_id
```

`correlation_id` groups related events in one operational flow.

`causation_id` links an event to its immediate triggering event where such a relationship exists.

## 8. Late and duplicate events

The platform is event-time aware.

Valid late-arriving events are accepted and processed according to their actual `event_time`.

Duplicate events are detected primarily by immutable `event_id` and handled idempotently.

Invalid future-dated events beyond the configured clock-skew tolerance are quarantined rather than silently rewritten.

## 9. Data quality

Every ingestion domain must support at least:

- schema validation
- required-field completeness
- datatype validation
- enumeration validation
- range validation
- referential integrity
- duplicate detection
- timestamp validation

Invalid records are quarantined while preserving:

- original payload
- source information
- failure reason

Quality status values:

```
PASS
WARN
FAIL
```

## 10. Schema versioning

Contracts use semantic versioning:

- **Patch** — backward-compatible correction or metadata change.
- **Minor** — backward-compatible field addition or optional extension.
- **Major** — breaking contract change.

Each producer and consumer must declare the schema version it supports.

## 11. Security and traceability

Secrets, credentials and access tokens must never be stored in event payloads or Git.

The system must maintain sufficient metadata to trace:

```
source
→ event
→ ingestion
→ transformation
→ curated record
→ analytical output
```

Reprocessable workloads must be idempotent, and processing must remain auditable.

## 12. Contract change control

A schema change requires:

1. Schema version update.
2. Change description.
3. Compatibility assessment.
4. Downstream impact assessment.

## Stage boundary

This document defines shared standards only.

It does **not** yet define the detailed telemetry schema.

The next stage will define the complete machine telemetry contract, including field names, datatypes, units, nullability, validation rules, machine-type applicability and example payloads.
