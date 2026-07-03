# Runtime V2.5B - Feature Activation Readiness Matrix

No feature is activated by this matrix.

- `controlled_memory_writes`: `explicit_approval_required`
- `controlled_recall`: `dry_run_only`
- `provider_live_trial`: `ready_for_human_review`
- `evaluator_live_trial`: `ready_for_human_review`
- `scheduler_dry_run`: `explicit_approval_required`
- `scheduler_live`: `blocked_by_safety`
- `hyb1_shadow`: `explicit_approval_required`
- `hyb1_promotion`: `blocked_by_safety`
- `training_dataset_export`: `ready_for_human_review`
- `training_job_execution`: `blocked_by_safety`
- `action_execution`: `blocked_by_safety`

Final recommendation: `PROCEED_CONTROLLED_TRAINING_DATASET_EXPORT_TRIAL`
