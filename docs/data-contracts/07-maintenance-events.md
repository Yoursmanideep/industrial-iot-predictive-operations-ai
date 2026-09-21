# 07 — Maintenance Events Contract

## Purpose

This contract defines the maintenance lifecycle used to inspect, repair, verify and return equipment to service.

It connects predictive insight and machine faults to physical maintenance activity:

```text
Prediction / Fault
      ↓
Maintenance Request
      ↓
Work Order
      ↓
Technician
      ↓
Inspection
      ↓
Repair + Parts
      ↓
Verification
      ↓
Return to Service
```

## Event types

| Event type | Purpose |
|---|---|
| MaintenanceRequested | Maintenance need is identified |
| WorkOrderCreated | Formal work order is created |
| TechnicianAssigned | Technician is assigned |
| MaintenanceInspectionStarted | Maintenance inspection begins |
| MaintenanceInspectionCompleted | Inspection result is recorded |
| RepairStarted | Repair activity begins |
| PartsConsumed | Spare-part consumption is recorded |
| RepairCompleted | Repair activity is completed |
| MaintenanceVerified | Repair outcome is verified |
| MachineReturnedToService | Maintenance workflow hands the machine back to operations |
| WorkOrderCancelled | Work order is cancelled |

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
machine_id
```

Optional context includes correlation_id, causation_id, line_id and machine_type.

## Maintenance identity

| Field | Meaning |
|---|---|
| maintenance_request_id | Initial maintenance request |
| work_order_id | Formal maintenance work order |
| technician_id | Assigned technician |
| supervisor_id | Supervisor where applicable |
| incident_id | Related operational incident |
| fault_event_id | Related machine-fault event |
| failure_mode_code | Governed failure classification |

## Maintenance types

Allowed values:

```text
CORRECTIVE
PREVENTIVE
PREDICTIVE
INSPECTION
EMERGENCY
CALIBRATION
```

Predictive maintenance should remain traceable to the prediction or operational condition that initiated it.

## Priority

Allowed values:

```text
LOW
MEDIUM
HIGH
CRITICAL
```

Priority represents operational urgency and is distinct from fault severity.

## Work-order lifecycle

Typical corrective flow:

```text
MaintenanceRequested
        ↓
WorkOrderCreated
        ↓
TechnicianAssigned
        ↓
MaintenanceInspectionStarted
        ↓
MaintenanceInspectionCompleted
        ↓
RepairStarted
        ↓
PartsConsumed
        ↓
RepairCompleted
        ↓
MaintenanceVerified
        ↓
MachineReturnedToService
```

Work orders may also be cancelled before completion.

## MaintenanceRequested

Required:

```text
maintenance_request_id
maintenance_type
priority
```

Possible initiators include predictive model output, machine fault, scheduled maintenance, operator report or inspection finding.

## WorkOrderCreated

Required:

```text
work_order_id
maintenance_type
priority
status
```

## TechnicianAssigned

Required:

```text
work_order_id
technician_id
```

## MaintenanceInspectionStarted

Required:

```text
work_order_id
technician_id
```

## MaintenanceInspectionCompleted

Required:

```text
work_order_id
inspection_result
```

Allowed results:

```text
PASS
FAIL
CONDITIONAL
NOT_REQUIRED
```

Diagnosis can be represented with diagnosis_code, diagnosis_notes and failure_mode_code.

## RepairStarted

Required:

```text
work_order_id
technician_id
status
```

## PartsConsumed

Required:

```text
work_order_id
part_id
part_quantity
part_uom
part_unit_cost_inr
```

Multiple parts-consumed events may exist for one work order.

This supports cost analysis by machine, plant, failure mode, part, technician and work order.

## RepairCompleted

Required:

```text
work_order_id
resolution_code
status
```

Optional measures include repair action, labor hours, maintenance cost and downtime duration.

## MaintenanceVerified

Required:

```text
work_order_id
inspection_result
status
```

Verification is independent from the technician's declaration that repair work is complete.

## MachineReturnedToService

Required:

```text
work_order_id
status = COMPLETED
```

The machine operating-state transition remains a machine operational event. This prevents the maintenance domain and machine-state domain from becoming competing sources of truth.

## WorkOrderCancelled

Required:

```text
work_order_id
cancel_reason_code
status = CANCELLED
```

## Cost semantics

Supported cost inputs:

```text
part_quantity
part_unit_cost_inr
labor_hours
maintenance_cost_inr
```

Analytical cost can later be calculated as parts cost + labor cost + other approved cost components, with derivation traceability.

## Downtime relationship

Maintenance events may carry downtime_duration_seconds.

Where causal linkage is known, use fault_event_id and incident_id.

This enables:

```text
Failure
  ↓
Maintenance
  ↓
Downtime
  ↓
Cost
  ↓
Recovery
```

## Predictive-maintenance relationship

When a maintenance request originates from an ML prediction, the eventual implementation should preserve the relationship through correlation or causation metadata.

Example:

```text
FailurePrediction
      ↓
MaintenanceRequested
      ↓
WorkOrderCreated
      ↓
RepairCompleted
      ↓
MachineReturnedToService
```

This later enables analysis of predicted risk, actual failure, intervention timing, avoided downtime and model false-positive/false-negative outcomes.

## Data-quality rules

Validate:

- event identity and event type
- plant and machine references
- work-order identity
- maintenance-request identity when supplied
- technician identity
- failure-mode identity when supplied
- maintenance type and priority
- status validity
- inspection result validity
- positive part quantity
- non-negative part cost
- non-negative labor hours
- non-negative maintenance cost
- timestamp validity
- duplicate event_id
- work-order lifecycle consistency

Invalid records are quarantined according to the global data standards.

## Idempotency

event_id is the duplicate-detection key.

Reprocessing must not duplicate technician assignments, part consumption, repair completion, maintenance cost or return-to-service events.

## Example — MaintenanceRequested

```json
{
  "event_id": "EVT-550e8400-e29b-41d4-a716-446655440030",
  "event_type": "MaintenanceRequested",
  "schema_version": "1.0.0",
  "event_time": "2026-09-21T08:05:00.000Z",
  "ingestion_time": "2026-09-21T08:05:00.150Z",
  "source_system": "maintenance_simulator",
  "plant_id": "PLT-CHN-01",
  "line_id": "CHN-L01",
  "machine_id": "CHN-L01-CNC01",
  "machine_type": "CNC",
  "maintenance_request_id": "MR-550e8400-e29b-41d4-a716-446655440031",
  "maintenance_type": "PREDICTIVE",
  "priority": "HIGH",
  "failure_mode_code": "CNC-BRG"
}
```

## Example — PartsConsumed

```json
{
  "event_id": "EVT-550e8400-e29b-41d4-a716-446655440032",
  "event_type": "PartsConsumed",
  "schema_version": "1.0.0",
  "event_time": "2026-09-21T10:42:11.000Z",
  "ingestion_time": "2026-09-21T10:42:11.180Z",
  "source_system": "cmms_simulator",
  "plant_id": "PLT-CHN-01",
  "line_id": "CHN-L01",
  "machine_id": "CHN-L01-CNC01",
  "work_order_id": "WO-550e8400-e29b-41d4-a716-446655440033",
  "part_id": "PART-SPINDLE-BRG42",
  "part_quantity": 1,
  "part_uom": "unit",
  "part_unit_cost_inr": 18500
}
```

## Example — MachineReturnedToService

```json
{
  "event_id": "EVT-550e8400-e29b-41d4-a716-446655440034",
  "event_type": "MachineReturnedToService",
  "schema_version": "1.0.0",
  "event_time": "2026-09-21T11:15:00.000Z",
  "ingestion_time": "2026-09-21T11:15:00.110Z",
  "source_system": "cmms_simulator",
  "plant_id": "PLT-CHN-01",
  "line_id": "CHN-L01",
  "machine_id": "CHN-L01-CNC01",
  "work_order_id": "WO-550e8400-e29b-41d4-a716-446655440033",
  "status": "COMPLETED"
}
```

## Contract version

Current version: **1.0.0**.

Breaking changes require a major version.
Backward-compatible additions use a minor version.
Metadata-only compatible corrections use a patch version.

## Stage boundary

This contract completes the core operational event domains for machine telemetry, machine operations, production, quality and maintenance.

The next stage will define the **reference-data contracts and controlled vocabularies** needed for products, suppliers, shifts, operators, spare parts and contextual API data.