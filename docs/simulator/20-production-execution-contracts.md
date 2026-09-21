# 20 — Production Execution Contracts

Stage 3.6 introduces explicit serializable state contracts for production orders and batches in addition to the canonical production-event contract.

Production order identity uses PO- plus deterministic UUID.

Batch identity uses BAT- plus deterministic UUID.

Production event identity uses EVT- plus deterministic UUID and is derived from run, entity, event type, event time and generation sequence.

The order quantity must reconcile to the sum of planned batch quantities.

During execution:

actual_quantity = good_quantity + rejected_quantity

at the event level, and cumulative order/batch quantities preserve the same invariant.

The line bottleneck is the minimum executable capacity across the machines required by the product route.

Scenario production multipliers reduce executable capacity and therefore create measurable SLOWDOWN losses when actual capacity falls below nominal capacity.

A route becomes DOWNTIME when a required machine is unavailable.

Pause and resume are explicit production events and can carry causation links to machine or operational events.

The stage is deliberately separated from future streaming integration. The current engine is deterministic and can later emit the same ProductionEvent objects to batch files, Eventstream or other ingestion adapters without changing business semantics.

## Next stage

Stage 3.6.1 — Enterprise-scale deterministic order generation and production event stream batching.