# 15 — Type-Specific Machine Behavior and Telemetry Physics

## Scope
Stage 3.5.3 converts the machine behavior interface into nine type-specific physical signal generators.

The generators are synthetic engineering models intended to create internally consistent telemetry for analytics and ML experiments. They are not claims about real equipment operating limits.

## Shared drivers
The physics layer consumes workload factor, machine health factor, ambient temperature, operating state, scenario severity and event time.

Two derived factors drive related signals:
- load — current workload intensity
- wear — the larger of health-derived degradation and scenario severity

Related signals therefore move together instead of behaving as independent random columns.

## Deterministic noise
Noise is derived from machine type, machine ID, event time and signal name.

A local seeded random generator is used for each signal. There is no mutable global random stream.

Same machine + same event time + same context produces the same telemetry.

## Type models

### CNC
Workload drives spindle speed, feed rate, power and production rate. Wear raises vibration and temperature and reduces quality.

### Hydraulic press
Workload drives hydraulic pressure, force, temperature and power. Wear causes pressure loss, thermal rise, cycle-time increase and quality decline.

### Industrial robot
Workload drives torque, motor temperature, power and throughput. Wear increases vibration, position error and cycle time.

### Conveyor
Workload drives belt speed, motor current, power and throughput. Wear increases vibration and temperature and reduces throughput.

### Compressor
Workload drives discharge pressure, RPM and power. Wear increases vibration and temperature and degrades pressure.

### Furnace
Workload drives chamber temperature, fuel flow and power. Wear creates thermal/pressure drift and quality reduction. Ambient temperature affects the thermal response.

### Inspection
Workload affects inspection cycle time and equipment temperature. Wear increases measurement deviation and defect probability.

### Packaging
Workload drives throughput, motor current and power. Wear increases cycle time/current/temperature and reduces throughput.

### Palletizer
Workload drives torque and power. Wear increases motor temperature, vibration and cycle-time drift.

## State interaction
RUNNING produces active production-related values.

For states where active production is stopped, production and throughput signals collapse toward zero. Monitoring signals such as temperature, current or vibration still provide machine-state context.

The state engine remains authoritative. Telemetry does not mutate machine state.

## Contract alignment
The physics registry contains exactly the nine machine types defined in the machine catalog.

Generated signal names are checked against the simulator machine profiles, which are cross-checked against the Stage 2.2 telemetry catalog.

Conveyor and Packaging use throughput_unit_min, matching their machine catalog definitions.

## Verification
Tests cover all nine providers, exact signal sets, deterministic repeatability, non-negative values, degradation-driven correlated changes and behavior-registry integration.

## Next stage
Stage 3.5.4 — Environment, workload, shift and production-context engine.