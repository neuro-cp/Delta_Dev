# RC1 First Activation Candidate

- phase: RC1 First Activation Candidate
- final_recommendation: `PROCEED_WAVE_0_MANUAL_RC1_VALIDATION_FIRST`

## Candidate

- candidate: fixture-only corpus ingestion into noncanonical semantic records
- do_not_activate_in_this_run: True
- command design: `.\.venv311\Scripts\python.exe scripts\delta_rc1_fixture_ingest.py --dry-run --input fixtures\rc1_corpus --output .tmp\rc1_activation\semantic_records`
- input folder: `fixtures/rc1_corpus`
- output folder: `.tmp/rc1_activation/semantic_records/<run_id>`

## Why Safest

It exercises the live-document-adapter bottleneck with local fixtures only, writes only to a noncanonical run workspace, requires no providers, and can be rolled back by deleting the run folder.

## Tests Required Before Activation

- parser handles malformed fixture without crash
- semantic records include provenance and source hash
- output path is noncanonical
- no provider/training/scheduler/memory/knowledge mutation flags change
- secret scan passes on generated records

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
