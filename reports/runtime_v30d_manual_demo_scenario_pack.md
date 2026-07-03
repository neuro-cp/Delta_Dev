# Runtime V3.0D Manual Demo Scenario Pack

## identity

Query: `What is DELTA?`

DELTA is a governed cognitive-runtime substrate in this repo. In the current local path it can describe its scaffold, safety boundaries, reports, and deterministic validation state without provider calls or memory mutation.

## capability_summary

Query: `What can you do?`

Currently active local capabilities: manual local console questions; deterministic current-state self-description; repo-local report and scaffold inspection; candidate-context recall when explicitly requested; static review console and dashboard artifacts; safety status and provenance reporting; deterministic validation/hardening reports.

Why this answer is local:
- matched: True
- topic: capabilities_active
- evidence items: 1
- provider required: False

Provenance:
- docs/ARCHITECTURE.md
- docs/INVARIANTS.md
- docs/ROADMAP.md
- docs/UPDATE.md
- reports/runtime_v25a_v27f_extended_overage_marathon_summary.md
- reports/runtime_v28_master_validation.md

## unknown_personal_fact

Query: `What did I eat for breakfast yesterday?`

I do not have sufficient governed local evidence to answer that directly. I can answer current repo-local questions about DELTA's architecture, capabilities, phase, safety, memory, recall, providers, HYB1, Model B, and scaffold status.

## memory_write_request

Query: `Can you remember my favorite color is blue?`

Memory writes and canonical writes remain disabled. Recall is candidate-context only and does not mutate runtime recall or canonical memory.

Why this answer is local:
- matched: True
- topic: memory_status
- evidence items: 1
- provider required: False

Provenance:
- docs/ARCHITECTURE.md
- docs/INVARIANTS.md
- docs/ROADMAP.md
- docs/UPDATE.md
- reports/runtime_v25a_v27f_extended_overage_marathon_summary.md
- reports/runtime_v28_master_validation.md

## hyb1_status

Query: `Is HYB1 active?`

HYB1 is dormant_env_gated_shadow_only; it is not promoted and is not the default.

## training_status

Query: `Can you train yourself?`

No. Training, fine-tuning, model weight updates, dataset export authority, and model artifact creation remain disabled.

## replay_consolidation_path

Query: `What is your replay and consolidation path?`

The current replay/consolidation path is: manual/raw message -> experience boundary/record -> episodic feedback capture -> replay markers/batches -> replay review -> consolidation candidate -> consolidation decision -> sleep-cycle plan -> canonical memory draft/record design. Canonical writes remain disabled.

Why this answer is local:
- matched: True
- topic: replay_consolidation
- evidence items: 1
- provider required: False

Provenance:
- docs/ARCHITECTURE.md
- docs/INVARIANTS.md
- docs/ROADMAP.md
- docs/UPDATE.md
- reports/runtime_v25a_v27f_extended_overage_marathon_summary.md
- reports/runtime_v28_master_validation.md

## full_pipeline_explanation

Query: `Explain how you answered that.`

Pipeline explanation

Input: What is DELTA?
Route matched: True (identity)
Matched alias: what is delta
Recall used: False (authoritative: False)
Evidence items: 1
Mutation status: none

Safety gates:
- provider_call_performed: False
- memory_write_performed: False
- recall_mutated: False
- training_triggered: False
- action_execution_performed: False
- scheduler_started: False
- hyb1_promoted: False
- model_b_default_changed: False

Final synthesis: DELTA is a governed cognitive-runtime substrate in this repo. In the current local path it can describe its scaffold, safety boundaries, reports, and deterministic validation state without provider calls or memory mutation.
