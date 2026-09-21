# Stage 2.7 — Reference Data Contract

## Purpose

This contract defines the governed reference and master-data domains used by the Industrial IoT platform. These values provide stable identities and controlled vocabularies for the simulator, ingestion validation, warehouse dimensions and analytics.

## Domains

| Domain | Grain | Immutable business key | Main relationship |
|---|---|---|---|
| Plant | One manufacturing plant | plant_id | Enterprise parent |
| Production Area | One area within a plant | production_area_id | Plant |
| Production Line | One production line | line_id | Production area / plant |
| Product | One manufactured product definition | product_id | Production order |
| Shift | One standard operating shift | shift_id | Plant operations |
| Operator | One production operator | operator_id | Shift / production execution |
| Technician | One maintenance technician | technician_id | Maintenance work order |
| Supplier | One supplier organization | supplier_id | Parts / materials |
| Spare Part | One spare-part definition | part_id | Supplier / maintenance |
| Failure Code | One governed failure mode | failure_mode_code | Machine / maintenance / ML labels |
| Alarm Code | One governed operational alarm | alarm_code | Machine operational events |
| Pause/Loss Reason | One governed production-loss reason | reason_code | Production events |
| Quality Defect Code | One governed defect definition | defect_code | Quality events |

## Common master-data rules

- Business keys are immutable once published.
- Reference records must have an explicit active/inactive lifecycle.
- Descriptive name changes must not change the business key.
- Every child record must reference an existing parent key.
- Codes are uppercase and use controlled formats.
- Effective dates are required whenever a value can change historically.
- Master-data changes must be auditable.

## Plant

Required fields:

```text
plant_id
plant_name
city
state
country
timezone
currency
status
effective_from
effective_to
```

Plant identities are defined in Stage 1.

## Production Area

Required fields:

```text
production_area_id
plant_id
area_name
status
effective_from
effective_to
```

## Production Line

Required fields:

```text
line_id
plant_id
production_area_id
line_name
line_type
status
effective_from
effective_to
```

Each line belongs to exactly one plant and one production area for a given effective period.

## Product

Required fields:

```text
product_id
product_name
product_family
product_category
unit_of_measure
standard_cycle_time_seconds
standard_unit_cost_inr
status
effective_from
effective_to
```

Products are reference definitions; production-order quantities remain transactional.

## Shift

Required fields:

```text
shift_id
shift_name
start_local
end_local
crosses_midnight
status
```

Shift IDs are governed globally. Local time interpretation uses the enterprise timezone.

## Operator

Required fields:

```text
operator_id
operator_name
plant_id
team_code
skill_level
status
effective_from
effective_to
```

Operator names are synthetic project data.

## Technician

Required fields:

```text
technician_id
technician_name
plant_id
specialization
skill_level
status
effective_from
effective_to
```

Technicians are maintenance-domain identities and are separate from production operators.

## Supplier

Required fields:

```text
supplier_id
supplier_name
supplier_type
country
lead_time_days
status
effective_from
effective_to
```

## Spare Part

Required fields:

```text
part_id
part_name
part_category
part_uom
standard_unit_cost_inr
minimum_stock_quantity
reorder_quantity
primary_supplier_id
status
effective_from
effective_to
```

A part may have multiple suppliers in future extensions; primary_supplier_id identifies the current preferred supplier only.

## Failure Code

Required fields:

```text
failure_mode_code
failure_category
failure_name
machine_type
severity_default
status
```

Failure codes must align with the Stage 1 failure taxonomy.

## Alarm Code

Required fields:

```text
alarm_code
alarm_name
alarm_category
default_severity
machine_type
trigger_signal
status
```

Alarm codes represent operational conditions and are not automatically equivalent to failure codes.

## Production Pause/Loss Reason

Required fields:

```text
reason_code
reason_name
reason_domain
loss_category
status
```

reason_domain values:

```text
PAUSE
LOSS
```

Loss categories:

```text
DOWNTIME
SLOWDOWN
SCRAP
QUALITY
MATERIAL
PLANNING
OTHER
```

## Quality Defect Code

Required fields:

```text
defect_code
defect_name
defect_category
default_severity
status
```

Defect categories align with the Stage 2.5 quality contract.

## Controlled vocabularies

### Lifecycle status

```text
ACTIVE
INACTIVE
```

### Machine criticality

```text
LOW
MEDIUM
HIGH
```

### Skill level

```text
LEVEL_1
LEVEL_2
LEVEL_3
LEVEL_4
LEVEL_5
```

### Supplier type

```text
OEM
AUTHORIZED_DISTRIBUTOR
LOCAL_VENDOR
RAW_MATERIAL_SUPPLIER
UTILITY_PROVIDER
```

## Reference-data governance

Reference data is not treated as random simulator configuration. It is a governed business layer.

Changes must preserve:

```text
identity
referential integrity
historical traceability
effective dating
version awareness
```

## Stage boundary

This stage defines reference-data contracts and controlled vocabularies. It does not yet create the large operator, supplier, product or spare-part transactional datasets.

The next stage will convert these contracts into the **physical simulator data model and seed/reference datasets**, which will then drive deterministic synthetic data generation.