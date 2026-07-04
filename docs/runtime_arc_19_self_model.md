# Runtime ARC 19 Self Model Runtime Awareness

This document describes the exhaustive, dedicated runtime module:

`orchestration/runtime/arc_19_self_model.py`

Implemented primitives:

- `SelfModel`
- `CapabilityInventory`
- `LimitationRegistry`
- `ConfidenceProfile`
- `RuntimeHealthState`
- `ActiveGoalRegistry`
- `PendingReviewRegistry`
- `RuntimeLoadModel`
- `SelfExplanationEngine`
- `SelfAudit`

The module provides object construction, validation, safety invariants, audit
summary, demo scenario, report payload, local answer hook, report generation,
and static dashboard generation.

Safety boundary:

- no training
- no provider calls or provider authority
- no autonomous browsing
- no tool execution
- no scheduler/background worker
- no memory mutation
- no knowledge mutation
- no HYB1 promotion
- Model B remains unchanged
