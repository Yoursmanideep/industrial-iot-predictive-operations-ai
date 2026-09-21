# 04 — Machine Operational Events Contract

## Purpose

This contract defines discrete operational events generated when a machine changes state, raises or clears an alarm, faults, recovers, or loses/regains communication.

It is intentionally separate from the telemetry contract:

Telemetry event = continuous measurement observation.
Operational event = discrete operational occurrence.

This separation lets the platform calculate event durations, downtime, state transitions, alarm lifecycles and incident timelines without inferring every operational fact from sensor readings alone.

## Event types

| Event type | Meaning |
|---|---|
| MachineStarted | Machine transitions into operation |
| MachineStopped | Machine stops operating |
| StateChanged | Machine moves between governed operating states |
| AlarmRaised | An active machine alarm begins |
| AlarmCleared | A previously raised alarm is cleared |
| MachineFaulted | Machine enters a fault condition |
| MachineRecovered | Machine enters a recovery phase |
| CommunicationLost | Expected machine communication is lost |
| CommunicationRestored | Communication returns after a gap |

## Common event envelope

Every event contains:

```text
event_id
event_type
schema_version
event_time
ingestion_time
source_system
plant_id
line_id
machine_id
machine_type
```

Optional traceability fields are correlation_id and causation_id.

## State semantics

Governed operating states are:

```text
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

For StateChanged events, previous_state and new_state are required and must differ.

The platform must not infer a state transition merely because telemetry stopped arriving.

## MachineStarted

Required: new_state = RUNNING.

## MachineStopped

Represents a discrete stop event. previous_state and new_state are required.

Whether a stop is planned is carried by is_planned when known.

## StateChanged

Represents an explicit state transition. Both previous_state and new_state are required.

Examples include RUNNING to STARVED and RUNNING to FAULT.

## AlarmRaised

Required:

```text
alarm_code
alarm_name
severity
operating_state
```

An alarm may occur while a machine continues running. AlarmRaised is therefore not automatically equivalent to MachineFaulted.

## AlarmCleared

Required: alarm_code and alarm_name.

The same alarm_code should be used to correlate the clear event with its corresponding raised alarm.

Clearing an alarm does not automatically mean that a machine has recovered from a fault.

## MachineFaulted

Required:

```text
fault_code
severity
operating_state = FAULT
```

When known, failure_mode_code links the event to the governed failure taxonomy.

## MachineRecovered

Represents a machine entering a recovery phase after a fault or maintenance action.

Required: previous_state and new_state = RECOVERY.

The later transition from RECOVERY to RUNNING should be represented separately as a StateChanged event.

## CommunicationLost

This is a connectivity event. It must not automatically be classified as a mechanical machine fault.

The distinction matters because absent telemetry can have different causes:

```text
Machine OFFLINE
versus
Machine communication failure
```

## CommunicationRestored

Required: communication_gap_seconds.

This supports communication availability and telemetry-availability analysis.

## Severity

Allowed values:

```text
INFO
LOW
MEDIUM
HIGH
CRITICAL
```

Severity describes operational impact. It is separate from data quality.

## Correlation and causation

correlation_id groups events belonging to one operational chain.

causation_id identifies the immediately triggering event when that relationship is known.

Example:

```text
AlarmRaised
    ↓
MachineFaulted
    ↓
IncidentCreated
    ↓
WorkOrderCreated
    ↓
MachineRecovered
```

## Temporal relationship with telemetry

Operational events and telemetry are related through machine identity and event time, but they do not require identical timestamps.

Example:

```text
14:31:58  telemetry — vibration 6.7 mm/s
14:32:01  telemetry — vibration 8.1 mm/s
14:32:03  AlarmRaised — VIBRATION_HIGH
14:32:05  MachineFaulted — CNC-BRG
```

This temporal chain will later support incident reconstruction and root-cause analysis.

## Idempotency

event_id is the primary duplicate-detection key.

Reprocessing the same event must not create a second logical operational event.

## Referential integrity

machine_id must resolve to the machine master.
line_id must resolve to the line associated with the machine.
plant_id must resolve to the plant associated with the line.
machine_type must agree with the machine master.

## Contract version

Current version: 1.0.0.

Breaking changes require a major version.
Backward-compatible additions use a minor version.
Metadata-only compatible corrections use a patch version.

## Stage boundary

This contract covers machine operational events only.

The next stage will define the production event contract covering production orders, batches, operations, unit production, schedule execution, completion and production losses.