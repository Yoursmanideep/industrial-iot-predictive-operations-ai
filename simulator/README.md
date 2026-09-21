# Industrial IoT Simulator

Stage 3.5.1 establishes the Python foundation for the deterministic industrial simulation engine.

Current scope:
- typed simulation run configuration
- deterministic identity and lineage utilities
- simulation clock
- mutable run context
- YAML generation-contract loading
- CLI entry point
- unit-test foundation

Design rules:
- one simulator run is the reproducibility boundary
- all generated records are traceable to simulator_run_id
- deterministic seed and configuration version are explicit
- generation sequence is monotonic within a run
- simulation time is separate from wall-clock execution time
- machine physics and failure behavior are added in later stages

Local setup:
1. python -m pip install -e ".[dev]"
2. industrial-sim --help
3. pytest
