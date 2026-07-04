# Runtime ARC 18 Multi-Time Memory Architecture

This document describes the exhaustive, dedicated runtime module:

`orchestration/runtime/arc_18_multitime_memory.py`

Implemented primitives:

- `ImmediateMemory`
- `WorkingMemory`
- `EpisodicMemory`
- `SemanticMemory`
- `ProceduralMemory`
- `LongTermMemory`
- `ArchiveMemory`
- `MemoryPromotionRules`
- `MemoryDecaySimulation`
- `MemoryAudit`

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
