# OV5 Activation Audit

- governance_preserved: True
- mutation_occurred: False
- expanded_read_only_activation_justified: True
- operator_signoff_required: True
- final_recommendation: `KEEP_EXPANSION_READ_ONLY_AND_OPERATOR_REVIEWED`

## Participating Capabilities

- fixture corpus loader: fixture_only
- semantic extraction: fixture_only
- proposition layer: read_only
- deduplication: read_only
- graph traversal: read_only
- hypothesis generation: read_only
- disconfirmation: read_only
- higher-order synthesis: read_only
- evaluation/regression loop: read_only_trial

## Blocked Capabilities

- live corpus ingestion: blocked
- provider-assisted evidence: blocked
- canonical writes: blocked
- training: blocked
- schedulers/background workers: blocked
- action execution: blocked
- HYB1 promotion: blocked
