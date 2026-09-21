# 09 — Physical Master Data Model

## Purpose

Stage 3.1 converts the reference-data contracts into an implementation-oriented relational master-data model.

The model is designed to support:

- stable business identifiers
- warehouse surrogate keys
- historical master-data analysis
- machine-to-line-to-plant lineage
- production and maintenance reference joins
- controlled code lookups
- data-quality validation
- future incremental/CDC-style master-data loading

## Schemas

```text
mdm   → enterprise and business master dimensions
ref   → controlled reference/code tables
audit → master-data quality results
```

## Core hierarchy

```text
dim_plant
    ↓
dim_production_area
    ↓
dim_line
    ↓
dim_machine
    ↓
machine telemetry / operations / maintenance facts
```

Machine model is separated from machine identity:

```text
dim_machine_model
        ↓
dim_machine
```

This avoids repeating manufacturer/model attributes across every machine record.

## Surrogate-key strategy

Each physical dimension contains a warehouse surrogate key ending in `_sk`.

Examples:

```text
plant_sk
line_sk
machine_model_sk
machine_sk
product_sk
operator_sk
technician_sk
supplier_sk
spare_part_sk
```

Business keys remain immutable:

```text
plant_id
line_id
machine_id
product_id
operator_id
technician_id
supplier_id
part_id
```

The future fact tables will use surrogate keys for analytical joins while business identifiers remain available for traceability.

## Historical dimensions

Dimensions where historical changes matter use:

```text
effective_from
effective_to
is_current
```

Initial SCD Type 2 candidates:

- production area
- production line
- machine
- machine model
- product
- operator
- technician
- supplier
- spare part

The purpose is to preserve the value that was valid when a historical event occurred.

Example:

```text
Machine CHN-L01-CNC01
Line = CHN-L01
valid through 2027-03-31

Machine CHN-L01-CNC01
Line = CHN-L03
valid from 2027-04-01
```

Historical telemetry should remain associated with the correct historical machine dimension row.

## Type 1-style dimensions

Shift is initially treated as a governed operating calendar/reference dimension because the standard shift definition is centrally controlled.

Controlled code tables are maintained under `ref`.

## Machine model separation

`dim_machine_model` contains attributes shared by multiple physical machines:

```text
machine_model_code
machine_type_code
manufacturer_name
model_name
model_description
```

`dim_machine` contains physical-asset attributes:

```text
machine_id
line_sk
machine_model_sk
machine_type_code
machine_sequence
serial_number
installation_date
rated_capacity
capacity_uom
operating limits
criticality
status
```

This allows 30 CNC machines to reference the same model definition without duplicating model metadata.

## Product master

The product dimension owns standard product characteristics:

```text
product_id
product_name
product_family
product_category
unit_of_measure
standard_cycle_time_seconds
standard_unit_cost_inr
```

Actual production quantities and production costs remain transactional and will not be stored in the product dimension.

## People master

Operators and maintenance technicians are separate entities.

Operators support production execution.

Technicians support maintenance execution.

This distinction prevents personnel from being incorrectly treated as interchangeable resources.

## Supplier and spare-part master

Spare parts reference a primary supplier through the supplier surrogate key.

The model supports:

```text
maintenance
   ↓
parts consumed
   ↓
spare part
   ↓
primary supplier
```

Later extensions may support a many-to-many supplier/part relationship without changing the core part identity.

## Governed reference tables

The following tables provide stable code lookups:

```text
ref.failure_mode
ref.alarm_code
ref.production_reason
ref.quality_defect
```

These align with the Stage 2 contracts.

Important distinction:

```text
alarm_code      = operational condition
failure_mode    = technical failure classification
defect_code     = quality outcome
reason_code     = production business reason
```

They must not be merged into one generic code table because their business semantics and ownership differ.

## Logical relationships

```text
Plant
  └── Production Area
        └── Line
              └── Machine
                    └── Machine Model

Plant ──< Operator
Plant ──< Technician

Supplier ──< Spare Part

Product ──< Production Order

Failure Mode ──< Machine Fault
Alarm Code ──< Machine Alarm
Production Reason ──< Production Loss/Pause
Quality Defect ──< Quality Defect Event
```

## Physical implementation principle

The SQL file deliberately keeps surrogate-key columns and logical relationships explicit without depending on database-enforced foreign-key behavior.

Referential integrity will be validated during master-data loading and data-quality processing.

This makes the model suitable for a layered analytical platform where the ingestion and quality framework owns validation.

## Master-data validation

At minimum, Stage 3 loading will check:

```text
duplicate business keys
missing parent keys
multiple current SCD2 rows
overlapping effective-date ranges
invalid status values
invalid controlled codes
machine/model type mismatch
line/plant hierarchy mismatch
invalid supplier references
negative numeric master values
```

Results are written to:

```text
audit.master_data_quality_result
```

## Stage boundary

Stage 3.1 defines the physical master-data structures.

It does not yet populate the large seed datasets or build the Python simulator.

The next stage will create **deterministic seed/reference data** for products, operators, technicians, suppliers, spare parts and machine models, then validate all hierarchy and reference relationships.