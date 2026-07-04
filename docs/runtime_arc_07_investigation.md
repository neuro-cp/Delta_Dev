# Runtime ARC 07 Collaborative Cognitive Investigation

This document describes the exhaustive, dedicated runtime module:

`orchestration/runtime/arc_07_investigation.py`

Implemented primitives:

- `Investigation`
- `ProblemDefinition`
- `KnowledgeGapAnalysis`
- `ResearchQuestion`
- `InvestigationPlan`
- `EvidenceCollectionPlan`
- `Finding`
- `InvestigationGraph`
- `InvestigationRecommendation`
- `MultiInvestigationState`
- `InvestigationReflection`
- `InvestigationTransaction`

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
