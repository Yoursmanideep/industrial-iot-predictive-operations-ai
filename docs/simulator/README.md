# Simulator Stage Map

The Python simulator now progresses through:

- Stage 3.5.1 — runtime foundation
- Stage 3.5.2 — machine state model
- Stage 3.5.3 — type-specific telemetry physics
- Stage 3.5.4 — environment, workload, shift and production context
- Stage 3.5.5 — scenario execution engine
- Stage 3.5.6 — scenario telemetry effects and operational events
- Stage 3.6 — production order, batch and line execution
- Stage 3.6.1 — enterprise-scale deterministic production generation
- Stage 3.7 — synchronized simulation clock
- Stage 3.8 — enterprise simulation runner

The Stage 3.7 coordinator is industrial_sim.simulation.step_engine.IntegratedSimulationStepEngine.

The Stage 3.8 runner is industrial_sim.simulation.runner.EnterpriseSimulationRunner.

The current simulator separates planning from execution:

1. Enterprise production generation creates deterministic orders and batches.
2. The synchronized step engine advances the physical world.
3. The enterprise runner streams telemetry, operational and production events to partitioned JSONL output.

Local setup:

1. python -m pip install -e ".[dev]"
2. industrial-sim --help
3. pytest