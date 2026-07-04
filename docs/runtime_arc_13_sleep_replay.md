# Runtime ARC 13 Sleep Cycle Replay Consolidation

This document describes the exhaustive, dedicated runtime module:

`orchestration/runtime/arc_13_sleep_replay.py`

Implemented primitives:

- `ReplaySchedulerSimulation`
- `ReplayBatchBuilder`
- `ReplayPriorityEngine`
- `ConsolidationPlanner`
- `DuplicateMergePlanner`
- `AbstractionProposal`
- `ForgettingProposal`
- `KnowledgeCompressionSimulation`
- `LongTermMemoryPlan`
- `SleepCycleState`
- `ReplayMetrics`
- `ConsolidationAudit`
- `ReplayTimeline`

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
