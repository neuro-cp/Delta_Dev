# TP20 - Training Necessity Reassessment

## Summary
Determine whether substrate evolution has reached a practical ceiling, without performing training.

## Activation State
report_only_decision_gate

## Operations
- review TP13 shadow training result
- compare substrate-first improvements against training governance costs
- decide whether evidence supports continuing substrate-first work
- hard-stop if training may be justified

## Evidence Inputs
- TP13 training protocol
- TP14 substrate-first findings
- TP19 external evaluation

## Outputs
- training necessity decision
- substrate-first evidence table
- training hard-stop review

## Metrics
- `safety_invariants_preserved`: 1.0
- `operator_review_preserved`: 1.0
- `rollback_path_defined`: 1.0
- `provenance_required`: 1.0
- `audit_required`: 1.0
- `deterministic_outputs`: 1.0
- `model_b_unchanged`: 1.0
- `hyb1_dormant`: 1.0
- `training_not_justified_by_evidence`: 1.0
- `substrate_first_supported`: 1.0

## Effect Size Estimates
- `retrieval_accuracy_delta_estimate`: 0.035
- `proposition_quality_delta_estimate`: 0.045
- `contradiction_visibility_delta_estimate`: 0.035
- `operator_review_burden_delta_estimate`: -0.02
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

## Training Decision
- conclusion: `CONTINUE_SUBSTRATE_FIRST`
- TP13 shadow artifact gains were too small relative to governance cost
- TP14 recovered the useful direction through substrate-first improvements
- TP15 provided governed integration design without weight changes

## Recommendation
`CONTINUE_SUBSTRATE_FIRST`

## Next Phase
TP21 Cognitive Cycle Integration
