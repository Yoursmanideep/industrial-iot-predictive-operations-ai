# 05 — Production Events Contract

## Purpose

This contract defines discrete manufacturing events for production-order lifecycle, batch execution, production output, pauses/resumptions, completion and explicit production-loss recording.

It bridges operational machine behavior and manufacturing business impact:

```
Machine / operational state
        ↓
Production execution
        ↓
Output / loss
```

The production contract does not require every production event to be tied to a machine because an order can exist before a physical machine assignment.

## Event types

| Event type | Purpose |
|---|---|
| ProductionOrderCreated | Production order is created |
| ProductionOrderReleased | Order is released for execution |
| ProductionStarted | Actual production execution begins |
| BatchStarted | Batch execution begins |
| UnitProduced | Production output is recorded |
| BatchCompleted | Batch reaches completion |
| ProductionPaused | Production execution pauses |
| ProductionResumed | Production execution resumes |
| ProductionCompleted | Production execution completes |
| ProductionLossRecorded | Production loss is explicitly recorded |

## Common event envelope

Required fields:

```
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

```
correlation_id
causation_id
line_id
machine_id
batch_id
product_id
operation_id
```

## Manufacturing identity

| Field | Meaning |
|---|---|
| production_order_id | Immutable production-order identifier |
| batch_id | Production batch identifier |
| product_id | Manufactured product identifier |
| operation_id | Specific manufacturing operation |
| production_sequence | Execution sequence within the order/process |

Relationship:

```
Production Order
  ├── Operation
  │     ├── Batch
  │     └── Batch
  └── Operation
        └── Batch
```

## Quantity semantics

The platform distinguishes:

```
planned_quantity
actual_quantity
good_quantity
rejected_quantity
loss_quantity
```

Core consistency rule:

```
good_quantity + rejected_quantity <= actual_quantity
```

Violations are treated as data-quality failures and are not silently corrected.

Allowed quantity units:

```
unit
kg
litre
meter
```

For the initial simulator, `unit` will be the primary output unit.

## Schedule semantics

Planned schedule:

```
planned_start_time
planned_end_time
```

Actual execution:

```
actual_start_time
actual_end_time
```

Keeping both allows schedule adherence and production-delay analysis.

Example:

```
Planned: 08:00 → 10:00
Actual:  08:17 → 10:31
```

## ProductionOrderCreated

Required:

```
product_id
planned_quantity
quantity_uom
planned_start_time
planned_end_time
```

The order exists but is not necessarily released to production.

## ProductionOrderReleased

Required:

```
product_id
planned_quantity
quantity_uom
```

Release indicates authorization for execution.

## ProductionStarted

Required:

```
product_id
line_id
actual_start_time
```

This marks actual execution commencement.

## BatchStarted

Required:

```
batch_id
product_id
line_id
actual_start_time
```

A batch represents a defined execution quantity or production grouping within an order.

## UnitProduced

Required:

```
batch_id
product_id
actual_quantity
good_quantity
rejected_quantity
quantity_uom
```

The implementation can emit individual unit events or short-interval aggregates. The simulator's final event grain will be decided during implementation.

## BatchCompleted

Required:

```
batch_id
actual_quantity
good_quantity
rejected_quantity
quantity_uom
actual_end_time
```

This gives the analytical layer an explicit batch completion boundary.

## ProductionPaused

Required:

```
line_id
pause_reason_code
```

A pause does not automatically mean machine failure.

Potential governed reasons include:

```
MATERIAL_STARVATION
PLANNED_CHANGEOVER
QUALITY_HOLD
MACHINE_FAULT
OPERATOR_SHORTAGE
UTILITY_INTERRUPTION
```

The controlled vocabulary will be maintained in reference configuration.

## ProductionResumed

Required:

```
line_id
actual_start_time
```

This closes the applicable production pause interval.

## ProductionCompleted

Required:

```
actual_quantity
good_quantity
rejected_quantity
quantity_uom
actual_end_time
```

This marks completion of the represented production scope.

## ProductionLossRecorded

This event explicitly records manufacturing impact.

Required:

```
loss_category
loss_reason_code
loss_quantity
quantity_uom
```

Loss categories:

```
DOWNTIME
SLOWDOWN
SCRAP
QUALITY
MATERIAL
PLANNING
OTHER
```

Optional causal linkage:

```
downtime_event_id
machine_fault_event_id
loss_duration_seconds
```

This allows a trace such as:

```
MachineFaulted
      ↓
ProductionPaused
      ↓
ProductionLossRecorded
      ↓
ProductionCompleted
```

without assuming every production loss came from a machine failure.

## Machine and downtime linkage

`machine_id` is optional because production can be represented at order or line level.

When a production loss is caused by a specific operational event, `downtime_event_id` should reference that event.

When a machine fault directly causes production impact, `machine_fault_event_id` may reference the corresponding `MachineFaulted` event.

This preserves a defensible causal chain.

## Correlation and causation

Use `correlation_id` to group events in the same manufacturing execution flow.

Use `causation_id` when one event directly triggers another.

Example:

```
ProductionOrderReleased
          ↓
ProductionStarted
          ↓
BatchStarted
          ↓
UnitProduced
          ↓
BatchCompleted
          ↓
ProductionCompleted
```

## Data-quality rules

The ingestion layer validates:

- event ID and event type
- production-order identity
- quantity non-negativity
- quantity-unit validity
- timestamp validity
- planned timestamp ordering
- actual timestamp ordering where applicable
- good/rejected/actual quantity consistency
- plant/line/machine referential integrity
- batch/product relationship
- duplicate event ID

Invalid records are quarantined according to the global data standards.

## Idempotency

`event_id` is the duplicate-detection key.

Reprocessing an event must not create duplicate production output or duplicate production-loss records.

## Example — ProductionStarted

```json
{
  "event_id": "EVT-550e8400-e29b-41d4-a716-446655440010",
  "event_type": "ProductionStarted",
  "schema_version": "1.0.0",
  "event_time": "2026-09-21T06:15:00.000Z",
  "ingestion_time": "2026-09-21T06:15:00.180Z",
  "source_system": "mes_simulator",
  "plant_id": "PLT-CHN-01",
  "line_id": "CHN-L01",
  "production_order_id": "PO-550e8400-e29b-41d4-a716-446655440011",
  "product_id": "PROD-MOTOR-A01",
  "actual_start_time": "2026-09-21T06:15:00.000Z"
}
```

## Example — ProductionLossRecorded

```json
{
  "event_id": "EVT-550e8400-e29b-41d4-a716-446655440012",
  "event_type": "ProductionLossRecorded",
  "schema_version": "1.0.0",
  "event_time": "2026-09-21T07:42:16.000Z",
  "ingestion_time": "2026-09-21T07:42:16.210Z",
  "source_system": "mes_simulator",
  "plant_id": "PLT-CHN-01",
  "line_id": "CHN-L01",
  "machine_id": "CHN-L01-CNC01",
  "production_order_id": "PO-550e8400-e29b-41d4-a716-446655440011",
  "batch_id": "BAT-550e8400-e29b-41d4-a716-446655440013",
  "product_id": "PROD-MOTOR-A01",
  "loss_category": "DOWNTIME",
  "loss_reason_code": "MACHINE_FAULT",
  "loss_quantity": 18,
  "quantity_uom": "unit",
  "loss_duration_seconds": 900,
  "downtime_event_id": "EVT-550e8400-e29b-41d4-a716-446655440014",
  "machine_fault_event_id": "EVT-550e8400-e29b-41d4-a716-446655440015"
}
```

## Contract version

Current version: **1.0.0**.

Breaking changes require a major version.

Backward-compatible additions use a minor version.

Metadata-only compatible corrections use a patch version.

## Stage boundary

This contract covers production execution events.

The next stage will define the **quality events contract**, covering inspections, measurements, defects, batch disposition and quality outcomes.
