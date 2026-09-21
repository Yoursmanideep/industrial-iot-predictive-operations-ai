# 08 — Reference Data & Controlled Vocabularies

## Purpose

Reference data is the governed master layer that stabilizes identities and allowed values across all event contracts.

Without this layer, the simulator could generate inconsistent plants, products, operators, parts or codes and the Fabric pipelines would have to guess what a value means.

## Reference domains

```text
Plant
  ↓
Production Area
  ↓
Production Line
  ↓
Machine

Product
Shift
Operator
Technician
Supplier
Spare Part
Failure Code
Alarm Code
Pause/Loss Reason
Quality Defect Code
```

## Stable identity rules

The following identifiers are treated as business keys:

```text
plant_id
production_area_id
line_id
machine_id
product_id
shift_id
operator_id
technician_id
supplier_id
part_id
failure_mode_code
alarm_code
reason_code
defect_code
```

Names and descriptions may change while business keys remain stable.

## Effective dating

Reference records that can change over time use:

```text
effective_from
effective_to
status
```

This allows the warehouse to answer historical questions without overwriting the past.

Example:

```text
Product A
standard_cycle_time = 42s
valid until 2027-03-31

Product A
standard_cycle_time = 39s
valid from 2027-04-01
```

The product identity remains the same.

## Domain-specific controls

### Plants and lines

Stage 1 already defines the three plants, their five lines and their 270-machine hierarchy. This stage provides the contract that future master datasets must conform to.

### Products

Products will provide standard process characteristics such as standard cycle time and standard unit cost. These values are reference assumptions; actual production quantities and costs remain event/transaction data.

### Operators

Operators are production personnel. They are intentionally separate from maintenance technicians.

### Technicians

Technicians belong to maintenance operations and carry maintenance specialization and skill metadata.

### Suppliers

Suppliers support spare-part and material provenance. Supplier data should later support lead-time and supply-risk analysis.

### Spare parts

Spare-part definitions support maintenance consumption, inventory analysis and maintenance cost.

### Failure codes

Failure codes must align with the Stage 1 failure taxonomy. They provide consistent labels for fault events, maintenance diagnoses and ML outcome labels.

### Alarm codes

Alarm codes describe machine operating conditions. They are not automatically failure diagnoses.

Example:

```text
VIBRATION_HIGH
      ≠
CNC-BRG
```

The first is an operational signal/condition; the second is a governed failure mode.

### Pause/loss reasons

Production pauses and production losses are separated from machine faults so business impact can be categorized without assuming a technical root cause.

### Quality defect codes

Defect codes provide stable labels for quality outcomes and ML supervision.

## Initial controlled values

The repository configuration defines initial values for:

- lifecycle status
- machine criticality
- technician/operator skill level
- supplier type
- shifts
- production pause reasons
- production loss reasons
- alarm codes
- quality defect codes

These values are intentionally small and extensible. New codes require controlled change rather than arbitrary simulator output.

## Relationship to event contracts

Reference data validates operational events:

```text
MachineTelemetry
    ↓ validate machine_id + machine_type + hierarchy

MachineFaulted
    ↓ validate failure_mode_code

AlarmRaised
    ↓ validate alarm_code

ProductionLossRecorded
    ↓ validate reason_code + loss_category

DefectDetected
    ↓ validate defect_code + defect_category

PartsConsumed
    ↓ validate part_id
```

## Data-quality expectations

Every reference record must satisfy:

- unique business key
- valid parent relationships
- controlled enumeration values
- valid effective-date interval
- no overlapping active versions for the same business key
- auditable change history

Reference-data failures are quarantined rather than silently repaired.

## Stage boundary

Stage 2.7 defines the reference-data contract and initial controlled vocabularies.

The next stage will turn these definitions into the **physical seed data model**, including products, operators, technicians, suppliers, spare parts and related reference records that the simulator can consume.