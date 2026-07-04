# RC1 Activation Wave Plan

- phase: RC1 Activation Wave Plan
- final_recommendation: `PROCEED_WAVE_0_MANUAL_RC1_VALIDATION`

## Activation Waves

### Wave 0: manual RC1 validation only
- purpose: Confirm the deterministic RC1 surfaces behave as claimed before enabling any live-ish capability.
- capabilities: evaluation/regression loop, grounded answer synthesis, read-only substrate retrieval
- entry criteria: RC1 adversarial validation passed; worktree clean or intentional changes only
- exit criteria: manual script passes; operator reviews readiness and safety outputs
- stop conditions: manual validation exits nonzero; safety flag changes; unexpected file/network/provider activity

### Wave 1: fixture corpus ingestion and semantic records
- purpose: Exercise parser and semantic-record shape on local fixtures only.
- capabilities: live document adapter, semantic record persistence
- entry criteria: Wave 0 passed; fixture folder allowlisted; noncanonical output folder selected
- exit criteria: fixture manifest generated; semantic records validate; no canonical writes
- stop conditions: schema validation failure; unexpected persistence target; provenance missing

### Wave 2: read-only retrieval and grounded synthesis
- purpose: Query noncanonical fixture records and synthesize grounded answers without mutating recall.
- capabilities: read-only substrate retrieval, grounded answer synthesis
- entry criteria: Wave 1 passed; fixture records validated
- exit criteria: answers cite fixture record ids; unsupported questions abstain; recall remains unmutated
- stop conditions: hallucinated evidence; missing uncertainty; mutation flag changes

### Wave 3: approval-gated simulated substrate writes
- purpose: Allow a single explicitly approved simulated write into a noncanonical trial store.
- capabilities: approval-gated substrate write
- entry criteria: Wave 2 passed; single candidate selected; exact approval phrase present
- exit criteria: one trial record written; audit metadata exists; rollback token exists
- stop conditions: approval ambiguity; overwatch block without owner override; missing rollback token

### Wave 4: rollback and evaluation validation
- purpose: Prove trial writes can be reversed and evaluated without side effects.
- capabilities: rollback execution, evaluation/regression loop, graph repair
- entry criteria: Wave 3 passed; rollback token present; pre-rollback audit complete
- exit criteria: rollback simulation passes; post-rollback evaluation passes; no destructive action
- stop conditions: rollback changes canonical store; evaluation starts scheduler; audit incomplete

### Wave 5: provider-assisted evidence, gated
- purpose: Use providers only as explicit evidence acquisition, never authority.
- capabilities: provider-assisted evidence, specialist deliberation
- entry criteria: Wave 4 passed; API/key gate explicit; cost cap; overwatch enabled
- exit criteria: provider result stored as evidence candidate only; no authority transfer; cost logged
- stop conditions: provider call without approval; authority flag true; secret leakage

### Wave 6: controlled live corpus pilot
- purpose: Run a small allowlisted local corpus through ingestion, retrieval, and review.
- capabilities: real corpus ingestion, semantic record persistence, read-only substrate retrieval
- entry criteria: Wave 5 optional or skipped; local corpus allowlist; operator approval
- exit criteria: bounded corpus manifest; semantic outputs validated; manual review complete
- stop conditions: storage cap exceeded; provenance missing; mutation outside workspace

### Wave 7: limited learning/consolidation pilot
- purpose: Run manual replay/consolidation over pilot records without autonomous learning.
- capabilities: replay batch persistence, consolidation candidate persistence, sleep/replay consolidation
- entry criteria: Wave 6 passed; manual replay batch selected; review path ready
- exit criteria: candidates are reviewable; decisions stay noncanonical; no scheduler
- stop conditions: batch duplication; silent integration; mutation flag changes


## Safety

- autonomous_browsing_performed: False
- autonomous_execution_performed: False
- background_worker_started: False
- fine_tuning_performed: False
- hidden_write_performed: False
- hyb1: dormant_env_gated
- knowledge_mutation_performed: False
- memory_mutation_performed: False
- model_b_default: unchanged
- model_update_performed: False
- provider_authority_granted: False
- provider_call_performed: False
- scheduler_started: False
- training_performed: False
