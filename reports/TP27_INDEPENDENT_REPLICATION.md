# TP27 - Independent Replication

## Summary
Repeat evaluations on fresh held-out datasets and confirm reproducibility.

## Activation State
controlled_noncanonical_or_report_only

## Operations
- freeze replication inputs
- run independent replication criteria as report-only evidence
- compare reproduced effects against earlier effect sizes

## Evidence Inputs
- TP19 independent evaluation
- TP26 large scale validation

## Outputs
- replication protocol
- reproducibility scorecard
- effect-size comparison

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
- `retrieval_accuracy_delta_estimate`: 0.056
- `proposition_quality_delta_estimate`: 0.073
- `contradiction_visibility_delta_estimate`: 0.063
- `operator_review_burden_delta_estimate`: -0.034
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
`PROCEED_TP28_PRODUCTION_READINESS_REVIEW`

## Next Phase
TP28 Production Readiness Review
