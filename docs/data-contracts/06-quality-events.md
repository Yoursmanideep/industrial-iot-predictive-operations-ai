# 06 — Quality Events Contract

## Purpose

This contract defines discrete quality events for inspection lifecycle, measurement results, defect detection, batch disposition, quality holds and rework.

It establishes quality as an independent data domain while preserving links to production and machine context:

```text
Machine condition
      ↓
Production execution
      ↓
Inspection / measurement
      ↓
Defect / quality outcome
      ↓
Acceptance / rejection / rework
```

The platform must distinguish an abnormal sensor condition from an actual quality defect. A telemetry anomaly is not automatically a quality failure.

## Event types

| Event type | Purpose |
|---|---|
| InspectionStarted | A defined inspection activity begins |
| InspectionCompleted | An inspection reaches an explicit result |
| MeasurementRecorded | A quality measurement is recorded |
| DefectDetected | A defect is formally identified |
| BatchAccepted | Batch passes defined quality disposition |
| BatchRejected | Batch fails defined quality disposition |
| QualityHoldPlaced | Batch is placed on quality hold |
| QualityHoldReleased | Quality hold is released with a disposition |
| ReworkStarted | Rework begins for affected quantity |
| ReworkCompleted | Rework finishes and quality status is evaluated |

## Common event envelope

Required:

```text
event_id
event_type
schema_version
event_time
ingestion_time
source_system
plant_id
production_order_id
```

Optional context:

```text
correlation_id
causation_id
line_id
machine_id
batch_id
product_id
operation_id
```

Quality events may reference a machine without making machine_id mandatory because inspection and batch disposition can occur at a line, cell or quality station level.

## Quality identity

| Field | Meaning |
|---|---|
| inspection_id | Identifier for one inspection activity |
| measurement_id | Identifier for one recorded measurement |
| defect_code | Controlled identifier for the observed defect |
| batch_id | Affected manufacturing batch |
| production_order_id | Parent manufacturing order |
| operation_id | Manufacturing operation under inspection |

## Inspection lifecycle

```text
InspectionStarted
       ↓
MeasurementRecorded (one or many)
       ↓
DefectDetected (zero or many)
       ↓
InspectionCompleted
       ↓
BatchAccepted / BatchRejected / QualityHoldPlaced
```

Not every inspection produces a defect, and not every quality event must immediately determine final batch disposition.

## InspectionStarted

Required:

```text
inspection_id
inspection_type
batch_id
product_id
```

Allowed inspection types:

```text
INLINE
FINAL
RANDOM
FIRST_ARTICLE
REWORK
```

## InspectionCompleted

Required:

```text
inspection_id
inspection_result
```

Allowed results:

```text
PASS
FAIL
CONDITIONAL
PENDING
```

Inspection completion does not by itself imply batch acceptance or rejection; disposition remains explicit.

## MeasurementRecorded

A measurement is an observed quality characteristic.

Required:

```text
measurement_id
measurement_name
measurement_value
measurement_uom
measurement_status
```

When available, include:

```text
target_value
lower_spec_limit
upper_spec_limit
```

Measurement status:

```text
IN_SPEC
OUT_OF_SPEC
NOT_EVALUATED
```

When both specification limits exist, an inclusive comparison should determine whether the measurement is within specification.

Example:

```text
Target: 25.00 mm
LSL:    24.95 mm
USL:    25.05 mm
Actual: 25.08 mm
Status: OUT_OF_SPEC
```

An out-of-spec measurement is quality evidence; it is not automatically a batch rejection.

## DefectDetected

Required:

```text
defect_code
defect_category
defect_severity
defect_quantity
defect_disposition
```

Defect categories:

```text
DIMENSIONAL
SURFACE
FUNCTIONAL
ASSEMBLY
MATERIAL
PROCESS
COSMETIC
OTHER
```

Defect disposition:

```text
SCRAP
REWORK
USE_AS_IS
PENDING
```

Possible severity values:

```text
LOW
MEDIUM
HIGH
CRITICAL
```

## BatchAccepted

Required:

```text
batch_id
inspection_result = PASS
```

This is an explicit production-quality disposition and should be traceable to the inspection activity through correlation and causation context.

## BatchRejected

Required:

```text
batch_id
inspection_result = FAIL
```

Rejection is an explicit business outcome. It should not be inferred solely from one sensor anomaly.

## QualityHoldPlaced

Required:

```text
batch_id
hold_reason_code
```

A hold means the final quality disposition is temporarily blocked.

Example reason codes:

```text
OUT_OF_SPEC_MEASUREMENT
UNRESOLVED_DEFECT
DOCUMENTATION_MISSING
SUPPLIER_MATERIAL_REVIEW
PROCESS_INVESTIGATION
```

## QualityHoldReleased

Required:

```text
batch_id
disposition_reason_code
```

Release means the hold condition has been resolved or a defined disposition has been reached. It does not by itself mean acceptance; an explicit BatchAccepted or BatchRejected event may follow.

## ReworkStarted

Required:

```text
batch_id
rework_quantity
rework_reason_code
```

Rework must retain the original production-order and batch lineage.

## ReworkCompleted

Required:

```text
batch_id
rework_quantity
inspection_result
```

Rework completion should be followed by the applicable quality verification process.

## Production relationship

Quality events reference the production order and, where applicable, batch and operation.

This enables:

```text
ProductionOrder
     ↓
Batch
     ↓
Inspection
     ↓
Measurement
     ↓
Defect
     ↓
Disposition
```

## Machine relationship

machine_id is optional because quality can be measured at:

- a machine
- a line
- a quality station
- a batch

When a defect or quality deviation can be linked to a machine, machine_id should be populated so later analytics can investigate machine-condition relationships.

## Distinguishing anomaly from defect

The platform must preserve the distinction:

```text
Telemetry anomaly
    ≠
Quality defect
```

For example, elevated vibration may increase defect probability without every elevated-vibration event producing a defect.

This distinction is essential for supervised ML training because quality labels must come from quality events rather than inferred sensor thresholds.

## Data-quality rules

Validate:

- event identity and controlled event type
- production-order reference
- batch/product relationships
- inspection identity
- measurement datatype and unit
- specification-limit consistency
- measurement status consistency
- defect quantity non-negativity
- rework quantity non-negativity
- controlled defect categories and dispositions
- valid inspection results
- valid plant/line/machine references
- duplicate event_id

Violations are quarantined according to the global data standards.

## Idempotency

`event_id` is the primary duplicate-detection key.

Reprocessing an event must not create duplicate inspections, defects, holds, dispositions or rework quantities.

## Example — MeasurementRecorded

```json
{
  "event_id": "EVT-550e8400-e29b-41d4-a716-446655440020",
  "event_type": "MeasurementRecorded",
  "schema_version": "1.0.0",
  "event_time": "2026-09-21T07:15:22.000Z",
  "ingestion_time": "2026-09-21T07:15:22.140Z",
  "source_system": "qms_simulator",
  "plant_id": "PLT-CHN-01",
  "line_id": "CHN-L01",
  "machine_id": "CHN-L01-CNC01",
  "production_order_id": "PO-550e8400-e29b-41d4-a716-446655440011",
  "batch_id": "BAT-550e8400-e29b-41d4-a716-446655440013",
  "product_id": "PROD-MOTOR-A01",
  "inspection_id": "INSP-550e8400-e29b-41d4-a716-446655440021",
  "measurement_id": "MEAS-550e8400-e29b-41d4-a716-446655440022",
  "measurement_name": "shaft_diameter",
  "measurement_value": 25.08,
  "target_value": 25.00,
  "lower_spec_limit": 24.95,
  "upper_spec_limit": 25.05,
  "measurement_uom": "mm",
  "measurement_status": "OUT_OF_SPEC"
}
```

## Contract version

Current version: **1.0.0**.

Breaking changes require a major version.
Backward-compatible additions use a minor version.
Metadata-only compatible corrections use a patch version.

## Stage boundary

This contract covers quality events only.

The next stage will define the **maintenance events contract**, covering maintenance requests, work orders, technician assignment, inspections, parts usage, repair, cost and return-to-service.