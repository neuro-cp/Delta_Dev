# Runtime E2E Semantic Consolidation Cycle

This harness is DELTA's first deterministic closed-loop semantic
consolidation test.

It simulates:

ExperienceRecord -> SemanticRecord -> ReplayBatch -> ConsolidationCandidate ->
ConsolidationDecision -> SimulatedConsolidatedKnowledge -> Inquiry ->
SemanticRetrieval -> EvidenceAssembly -> GroundedSynthesis ->
AnswerWithUncertainty

It does not perform model training, fine-tuning, provider calls, autonomous
learning, canonical memory mutation, live knowledge mutation, or default runtime
behavior changes.

The fixture scenario asks why Project Atlas failed, what fixed it, and what
remains uncertain. The expected answer must be grounded only in simulated
semantic/consolidated records and must identify Worker C execution as still
uncertain.

Run:

```powershell
.\.venv311\Scripts\python.exe scripts\delta_e2e_semantic_cycle.py
```

Generated artifacts:

- `reports/runtime_e2e_semantic_consolidation_cycle.md`
- `reports/runtime_e2e_semantic_consolidation_cycle.json`
- `ui/delta_e2e_semantic_consolidation_cycle.html`
