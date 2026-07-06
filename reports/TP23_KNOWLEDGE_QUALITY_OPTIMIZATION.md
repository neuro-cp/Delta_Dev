# TP23 - Knowledge Quality Optimization

## Summary
Improve proposition normalization, contradiction handling, uncertainty calibration, and provenance quality.

## Activation State
controlled_noncanonical_or_report_only

## Operations
- define proposition-quality checks
- preserve contradiction visibility
- calibrate uncertainty without inflating confidence
- require provenance completeness before higher confidence

## Evidence Inputs
- TP14 proposition and uncertainty findings
- TP22 replay optimization

## Outputs
- knowledge quality scorecard
- contradiction preservation review
- provenance quality review

## Metrics
- `safety_invariants_preserved`: 1.0
- `operator_review_preserved`: 1.0
- `rollback_path_defined`: 1.0
- `provenance_required`: 1.0
- `audit_required`: 1.0
- `deterministic_outputs`: 1.0
- `model_b_unchanged`: 1.0
- `hyb1_dormant`: 1.0

## Effect Size Estimates
- `retrieval_accuracy_delta_estimate`: 0.044
- `proposition_quality_delta_estimate`: 0.057
- `contradiction_visibility_delta_estimate`: 0.047
- `operator_review_burden_delta_estimate`: -0.026
- `rollback_success_target`: 1.0

## Safety
- `model_training_performed`: False
- `fine_tuning_performed`: False
- `weight_update_performed`: False
- `checkpoint_created`: False
- `lora_or_adapter_created`: False
- `model_replaced`: False
- `production_deployment_performed`: False
- `baseline_routing_changed`: False
- `provider_authority_enabled`: False
- `provider_call_performed`: False
- `canonical_write_performed`: False
- `irreversible_canonical_migration_performed`: False
- `autonomous_memory_enabled`: False
- `autonomous_action_performed`: False
- `scheduler_started`: False
- `hyb1_promoted`: False
- `model_b_default_changed`: False

## Recommendation
`PROCEED_TP24_RUNTIME_OPTIMIZATION`

## Next Phase
TP24 Runtime Optimization
