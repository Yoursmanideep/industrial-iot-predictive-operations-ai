# 03 — Machine Telemetry Contract

## Purpose

This contract defines the canonical streaming telemetry event emitted by the machine simulator and accepted by the Industrial IoT platform.

The contract is designed so that:

1. Every telemetry record has a stable event envelope.
2. Event time and ingestion time remain separate.
3. Machine identity and hierarchy are explicit.
4. Machine-type-specific signals are represented without pretending every machine has identical sensors.
5. Measurements use canonical units.
6. Numeric ranges are validated at ingestion.
7. The contract is versioned independently from implementation code.

## Event identity

Every telemetry message represents one machine observation at a point in time.

```
event_id
event_type = MachineTelemetry
schema_version
event_time
ingestion_time
source_system
```

`event_id` is immutable and globally unique.

## Minimum event envelope

| Field | Type | Required | Rule |
|---|---|---:|---|
| event_id | string | Yes | `EVT-{UUID}` |
| event_type | string | Yes | Must be `MachineTelemetry` |
| schema_version | string | Yes | Semantic version |
| event_time | datetime | Yes | UTC, ISO-8601 |
| ingestion_time | datetime | Yes | UTC, ISO-8601 |
| source_system | string | Yes | Non-empty |
| correlation_id | string | No | Operational correlation |
| causation_id | string | No | Immediate causation reference |
| plant_id | string | Yes | Valid plant ID |
| line_id | string | Yes | Valid line ID |
| machine_id | string | Yes | Valid machine ID |
| machine_type | enum | Yes | Controlled machine type |
| operating_state | enum | Yes | Controlled operating state |

## Machine-specific signal profiles

### CNC

Required signals:

- spindle_rpm
- vibration_mm_s
- temperature_c
- pressure_bar
- power_kw
- feed_rate_mm_min
- production_rate_unit_min
- quality_score_pct

### Hydraulic Press

Required signals:

- hydraulic_pressure_bar
- temperature_c
- force_kn
- cycle_time_s
- power_kw
- production_rate_unit_min
- quality_score_pct

### Industrial Robot

Required signals:

- motor_temperature_c
- torque_nm
- vibration_mm_s
- position_error_mm
- cycle_time_s
- power_kw
- production_rate_unit_min

### Conveyor

Required signals:

- motor_current_a
- belt_speed_m_s
- vibration_mm_s
- temperature_c
- power_kw
- production_rate_unit_min

### Compressor

Required signals:

- discharge_pressure_bar
- temperature_c
- vibration_mm_s
- rpm
- power_kw

### Furnace

Required signals:

- chamber_temperature_c
- fuel_flow_rate
- pressure_mbar
- power_kw
- cycle_time_s
- quality_score_pct

### Inspection

Required signals:

- inspection_cycle_time_s
- measurement_deviation_mm
- defect_probability_pct
- equipment_temperature_c

### Packaging

Required signals:

- cycle_time_s
- production_rate_unit_min
- motor_current_a
- temperature_c
- power_kw

### Palletizer

Required signals:

- cycle_time_s
- motor_temperature_c
- torque_nm
- vibration_mm_s
- cycle_time_s
- power_kw

## Signal rules

The JSON Schema contains the canonical datatype, unit, absolute validation limits and operating bands for every defined signal.

Three operational bands are used:

- **Normal** — expected operation.
- **Warning** — abnormal behavior requiring investigation or monitoring.
- **Critical** — severe condition suitable for operational alerting.

The absolute invalid range is different from a critical range. A critical value may represent a physically valid but dangerous machine condition; an invalid value is treated as a data-quality problem.

This distinction is important for the real-time pipeline because:

```
valid + critical
≠
invalid data
```

## Nullability

Sensor properties are nullable because a canonical event envelope is shared across machine types.

However:

- Signals required by the declared machine type must contain a value.
- Signals not applicable to that machine type must not be fabricated.
- A non-applicable signal is represented as `NULL` when the implementation uses a wide canonical storage schema.
- The simulator must never generate invented values merely to satisfy a wide table.

## Timestamp rules

`event_time` is the physical measurement time.

`ingestion_time` is assigned by the platform when the event is received.

These values may legitimately differ because of network or processing delay.

Out-of-order events are valid when their event time is valid.

Duplicate events are identified by `event_id`.

## Referential rules

Telemetry must reference an existing:

```
plant_id
  ↓
line_id
  ↓
machine_id
```

The declared `machine_type` must match the machine master record.

These referential checks occur after schema validation and before curated loading.

## Example — CNC telemetry

```json
{
  "event_id": "EVT-550e8400-e29b-41d4-a716-446655440000",
  "event_type": "MachineTelemetry",
  "schema_version": "1.0.0",
  "event_time": "2026-09-21T05:16:23.145Z",
  "ingestion_time": "2026-09-21T05:16:23.392Z",
  "source_system": "iiot_simulator",
  "correlation_id": null,
  "causation_id": null,
  "plant_id": "PLT-CHN-01",
  "line_id": "CHN-L01",
  "machine_id": "CHN-L01-CNC01",
  "machine_type": "CNC",
  "operating_state": "RUNNING",
  "temperature_c": 62.4,
  "vibration_mm_s": 3.1,
  "pressure_bar": 116.8,
  "spindle_rpm": 4210,
  "power_kw": 31.7,
  "feed_rate_mm_min": 1350,
  "production_rate_unit_min": 18.4,
  "quality_score_pct": 98.7
}
```

## Example — anomaly telemetry

An anomaly is still valid telemetry when the measurement is within the physical validity envelope.

```json
{
  "event_type": "MachineTelemetry",
  "machine_type": "CNC",
  "operating_state": "RUNNING",
  "temperature_c": 96.2,
  "vibration_mm_s": 9.1,
  "pressure_bar": 109.4,
  "spindle_rpm": 3980,
  "power_kw": 44.6,
  "feed_rate_mm_min": 1210,
  "production_rate_unit_min": 14.7,
  "quality_score_pct": 91.4
}
```

This should be classified as an operationally abnormal observation, not automatically rejected as bad data.

## Example — invalid telemetry

```json
{
  "temperature_c": -500
}
```

This violates the absolute physical/data validity constraint and must be rejected or quarantined according to the ingestion quality rules.

## Storage implication

The streaming contract is a logical event contract.

When persisted in Bronze, the raw event may be retained in its source representation.

When converted to Silver/curated storage, the implementation may use:

- a wide telemetry table for common analytical access, or
- a normalized observation model where sensor metadata is separated from measurements.

The final physical storage design will be decided during the Fabric data-model stage rather than being forced by this event contract.

## Contract version

Current version: **1.0.0**

Breaking changes require a major version.

Backward-compatible field additions may use a minor version.

Metadata-only backward-compatible corrections may use a patch version.

## Stage boundary

This contract defines streaming machine telemetry only.

The next contract will define **machine operational events** such as start, stop, fault, alarm raised/cleared, recovery and state changes.
