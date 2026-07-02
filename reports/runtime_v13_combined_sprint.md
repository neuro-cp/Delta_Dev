# Runtime V1.3 Combined Sprint

Final decision: `KEEP_USAGE_GATE_ONLY_RUN_MORE_DIAGNOSTICS`

## Sprint Summary

Do not enable activation recurrence by default. Keep the accepted reasoning usage gate and continue diagnostics.

## Frozen-Boundary Verification

- `learning_changed`: `False`
- `governance_changed`: `False`
- `provider_prompts_changed`: `False`
- `canonical_storage_changed`: `False`
- `activation_recurrence_default_enabled`: `False`
- `usage_gate_enabled`: `True`

## Variant Table

| Variant | Live | Accepted | Retrieval Recall | Attention Precision | Noise Used | Mean Expected Rank | Mean Noise Above Expected |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| baseline_reference | `False` | `False` | `0.5333` | `0.55` | `12.0` | `10` | `9.7083` |
| usage_gate_only | `True` | `False` | `0.5333` | `0.55` | `12.0` | `10` | `9.7083` |
| combined_conservative | `True` | `False` | `0.5667` | `0.4172` | `24.0` | `7.2174` | `7.0417` |
| combined_tiebreaker | `True` | `False` | `0.5333` | `0.5` | `13.0` | `9.8261` | `9.5417` |
| metadata_usage_gate | `True` | `False` | `0.5333` | `0.55` | `12.0` | `10` | `9.7083` |

## Variant Comparisons

### baseline_reference

Preserved V1.2 baseline reports; no runtime command executed.

Acceptance:
- `commands_succeeded`: `True`
- `read_only_verified`: `True`
- `grounding_score_remains_1`: `True`
- `hallucinations_remain_0`: `True`
- `confidence_calibration_not_regress`: `True`
- `planning_score_not_regress`: `True`
- `retrieval_recall_not_regress`: `True`
- `expected_outside_top10_not_regress`: `True`
- `expected_outside_top20_not_regress`: `True`
- `mean_expected_rank_improves`: `False`
- `mean_noise_above_expected_improves`: `False`
- `no_expected_top10_pushed_out`: `True`
- `noise_used_in_reasoning_not_increase`: `True`
- `reasoning_drift_cases_not_increase`: `True`
- `attention_precision_not_materially_regress`: `True`
- `attention_recall_not_materially_regress`: `True`
- `planning_core_coverage_not_regress`: `True`
- `response_core_coverage_not_regress`: `True`
- `sparse_behavior_not_regress`: `True`

Per-case changes:

| Case | Noise | Attention Precision | Decision | Planning Core | Response Core |
| --- | --- | --- | --- | --- | --- |
| planning_failed_assumption | `0 -> 0` | `1.0 -> 1.0` | `Under-Attending -> Under-Attending` | `0.6667 -> 0.6667` | `0.6667 -> 0.6667` |
| causal_industrial_failure | `6 -> 6` | `0.25 -> 0.25` | `Reasoning Drift -> Reasoning Drift` | `0.6667 -> 0.6667` | `0.6667 -> 0.6667` |
| contradictory_evidence | `1 -> 1` | `0.0 -> 0.0` | `Reasoning Drift -> Reasoning Drift` | `0.0 -> 0.0` | `0.0 -> 0.0` |
| resource_allocation_shelters | `1 -> 1` | `0.0 -> 0.0` | `Reasoning Drift -> Reasoning Drift` | `0.0 -> 0.0` | `0.0 -> 0.0` |
| risk_uncertainty_planning | `1 -> 1` | `0.0 -> 0.0` | `Reasoning Drift -> Reasoning Drift` | `0.0 -> 0.0` | `0.0 -> 0.0` |
| policy_audit_conflict | `0 -> 0` | `1.0 -> 1.0` | `Planning Drift -> Planning Drift` | `0.3333 -> 0.3333` | `0.3333 -> 0.3333` |
| multi_step_failure_revision | `3 -> 3` | `0.25 -> 0.25` | `Reasoning Drift -> Reasoning Drift` | `0.3333 -> 0.3333` | `0.3333 -> 0.3333` |
| logistics_proxy_planning | `0 -> 0` | `1.0 -> 1.0` | `Under-Attending -> Under-Attending` | `0.3333 -> 0.3333` | `0.3333 -> 0.3333` |
| sparse_violin_tuning | `0 -> 0` | `1.0 -> 1.0` | `Healthy -> Healthy` | `1.0 -> 1.0` | `1.0 -> 1.0` |
| unsupported_recipe | `0 -> 0` | `1.0 -> 1.0` | `Healthy -> Healthy` | `1.0 -> 1.0` | `1.0 -> 1.0` |

### usage_gate_only

Accepted reasoning usage gate with activation recurrence disabled.

Acceptance:
- `commands_succeeded`: `True`
- `read_only_verified`: `True`
- `grounding_score_remains_1`: `True`
- `hallucinations_remain_0`: `True`
- `confidence_calibration_not_regress`: `True`
- `planning_score_not_regress`: `True`
- `retrieval_recall_not_regress`: `True`
- `expected_outside_top10_not_regress`: `True`
- `expected_outside_top20_not_regress`: `True`
- `mean_expected_rank_improves`: `False`
- `mean_noise_above_expected_improves`: `False`
- `no_expected_top10_pushed_out`: `True`
- `noise_used_in_reasoning_not_increase`: `True`
- `reasoning_drift_cases_not_increase`: `True`
- `attention_precision_not_materially_regress`: `True`
- `attention_recall_not_materially_regress`: `True`
- `planning_core_coverage_not_regress`: `True`
- `response_core_coverage_not_regress`: `True`
- `sparse_behavior_not_regress`: `True`

Per-case changes:

| Case | Noise | Attention Precision | Decision | Planning Core | Response Core |
| --- | --- | --- | --- | --- | --- |
| planning_failed_assumption | `0 -> 0` | `1.0 -> 1.0` | `Under-Attending -> Under-Attending` | `0.6667 -> 0.6667` | `0.6667 -> 0.6667` |
| causal_industrial_failure | `6 -> 6` | `0.25 -> 0.25` | `Reasoning Drift -> Reasoning Drift` | `0.6667 -> 0.6667` | `0.6667 -> 0.6667` |
| contradictory_evidence | `1 -> 1` | `0.0 -> 0.0` | `Reasoning Drift -> Reasoning Drift` | `0.0 -> 0.0` | `0.0 -> 0.0` |
| resource_allocation_shelters | `1 -> 1` | `0.0 -> 0.0` | `Reasoning Drift -> Reasoning Drift` | `0.0 -> 0.0` | `0.0 -> 0.0` |
| risk_uncertainty_planning | `1 -> 1` | `0.0 -> 0.0` | `Reasoning Drift -> Reasoning Drift` | `0.0 -> 0.0` | `0.0 -> 0.0` |
| policy_audit_conflict | `0 -> 0` | `1.0 -> 1.0` | `Planning Drift -> Planning Drift` | `0.3333 -> 0.3333` | `0.3333 -> 0.3333` |
| multi_step_failure_revision | `3 -> 3` | `0.25 -> 0.25` | `Reasoning Drift -> Reasoning Drift` | `0.3333 -> 0.3333` | `0.3333 -> 0.3333` |
| logistics_proxy_planning | `0 -> 0` | `1.0 -> 1.0` | `Under-Attending -> Under-Attending` | `0.3333 -> 0.3333` | `0.3333 -> 0.3333` |
| sparse_violin_tuning | `0 -> 0` | `1.0 -> 1.0` | `Healthy -> Healthy` | `1.0 -> 1.0` | `1.0 -> 1.0` |
| unsupported_recipe | `0 -> 0` | `1.0 -> 1.0` | `Healthy -> Healthy` | `1.0 -> 1.0` | `1.0 -> 1.0` |

### combined_conservative

Bounded activation recurrence penalty plus usage gate.

Acceptance:
- `commands_succeeded`: `True`
- `read_only_verified`: `True`
- `grounding_score_remains_1`: `True`
- `hallucinations_remain_0`: `True`
- `confidence_calibration_not_regress`: `True`
- `planning_score_not_regress`: `True`
- `retrieval_recall_not_regress`: `True`
- `expected_outside_top10_not_regress`: `True`
- `expected_outside_top20_not_regress`: `True`
- `mean_expected_rank_improves`: `True`
- `mean_noise_above_expected_improves`: `True`
- `no_expected_top10_pushed_out`: `True`
- `noise_used_in_reasoning_not_increase`: `False`
- `reasoning_drift_cases_not_increase`: `False`
- `attention_precision_not_materially_regress`: `False`
- `attention_recall_not_materially_regress`: `True`
- `planning_core_coverage_not_regress`: `True`
- `response_core_coverage_not_regress`: `True`
- `sparse_behavior_not_regress`: `True`

Per-case changes:

| Case | Noise | Attention Precision | Decision | Planning Core | Response Core |
| --- | --- | --- | --- | --- | --- |
| planning_failed_assumption | `0 -> 1` | `1.0 -> 0.5` | `Under-Attending -> Reasoning Drift` | `0.6667 -> 0.3333` | `0.6667 -> 0.3333` |
| causal_industrial_failure | `6 -> 7` | `0.25 -> 0.2222` | `Reasoning Drift -> Reasoning Drift` | `0.6667 -> 0.6667` | `0.6667 -> 0.6667` |
| contradictory_evidence | `1 -> 2` | `0.0 -> 0.0` | `Reasoning Drift -> Reasoning Drift` | `0.0 -> 0.0` | `0.0 -> 0.0` |
| resource_allocation_shelters | `1 -> 1` | `0.0 -> 0.0` | `Reasoning Drift -> Reasoning Drift` | `0.0 -> 0.0` | `0.0 -> 0.0` |
| risk_uncertainty_planning | `1 -> 8` | `0.0 -> 0.2` | `Reasoning Drift -> Reasoning Drift` | `0.0 -> 0.6667` | `0.0 -> 0.6667` |
| policy_audit_conflict | `0 -> 1` | `1.0 -> 0.5` | `Planning Drift -> Reasoning Drift` | `0.3333 -> 0.3333` | `0.3333 -> 0.3333` |
| multi_step_failure_revision | `3 -> 3` | `0.25 -> 0.25` | `Reasoning Drift -> Reasoning Drift` | `0.3333 -> 0.3333` | `0.3333 -> 0.3333` |
| logistics_proxy_planning | `0 -> 1` | `1.0 -> 0.5` | `Under-Attending -> Reasoning Drift` | `0.3333 -> 0.3333` | `0.3333 -> 0.3333` |
| sparse_violin_tuning | `0 -> 0` | `1.0 -> 1.0` | `Healthy -> Healthy` | `1.0 -> 1.0` | `1.0 -> 1.0` |
| unsupported_recipe | `0 -> 0` | `1.0 -> 1.0` | `Healthy -> Healthy` | `1.0 -> 1.0` | `1.0 -> 1.0` |

### combined_tiebreaker

Micro-penalty/tiebreaker recurrence signal plus usage gate.

Acceptance:
- `commands_succeeded`: `True`
- `read_only_verified`: `True`
- `grounding_score_remains_1`: `True`
- `hallucinations_remain_0`: `True`
- `confidence_calibration_not_regress`: `True`
- `planning_score_not_regress`: `True`
- `retrieval_recall_not_regress`: `True`
- `expected_outside_top10_not_regress`: `True`
- `expected_outside_top20_not_regress`: `True`
- `mean_expected_rank_improves`: `True`
- `mean_noise_above_expected_improves`: `True`
- `no_expected_top10_pushed_out`: `True`
- `noise_used_in_reasoning_not_increase`: `False`
- `reasoning_drift_cases_not_increase`: `False`
- `attention_precision_not_materially_regress`: `True`
- `attention_recall_not_materially_regress`: `True`
- `planning_core_coverage_not_regress`: `True`
- `response_core_coverage_not_regress`: `True`
- `sparse_behavior_not_regress`: `True`

Per-case changes:

| Case | Noise | Attention Precision | Decision | Planning Core | Response Core |
| --- | --- | --- | --- | --- | --- |
| planning_failed_assumption | `0 -> 0` | `1.0 -> 1.0` | `Under-Attending -> Under-Attending` | `0.6667 -> 0.6667` | `0.6667 -> 0.6667` |
| causal_industrial_failure | `6 -> 6` | `0.25 -> 0.25` | `Reasoning Drift -> Reasoning Drift` | `0.6667 -> 0.6667` | `0.6667 -> 0.6667` |
| contradictory_evidence | `1 -> 1` | `0.0 -> 0.0` | `Reasoning Drift -> Reasoning Drift` | `0.0 -> 0.0` | `0.0 -> 0.0` |
| resource_allocation_shelters | `1 -> 1` | `0.0 -> 0.0` | `Reasoning Drift -> Reasoning Drift` | `0.0 -> 0.0` | `0.0 -> 0.0` |
| risk_uncertainty_planning | `1 -> 1` | `0.0 -> 0.0` | `Reasoning Drift -> Reasoning Drift` | `0.0 -> 0.0` | `0.0 -> 0.0` |
| policy_audit_conflict | `0 -> 1` | `1.0 -> 0.5` | `Planning Drift -> Reasoning Drift` | `0.3333 -> 0.3333` | `0.3333 -> 0.3333` |
| multi_step_failure_revision | `3 -> 3` | `0.25 -> 0.25` | `Reasoning Drift -> Reasoning Drift` | `0.3333 -> 0.3333` | `0.3333 -> 0.3333` |
| logistics_proxy_planning | `0 -> 0` | `1.0 -> 1.0` | `Under-Attending -> Under-Attending` | `0.3333 -> 0.3333` | `0.3333 -> 0.3333` |
| sparse_violin_tuning | `0 -> 0` | `1.0 -> 1.0` | `Healthy -> Healthy` | `1.0 -> 1.0` | `1.0 -> 1.0` |
| unsupported_recipe | `0 -> 0` | `1.0 -> 1.0` | `Healthy -> Healthy` | `1.0 -> 1.0` | `1.0 -> 1.0` |

### metadata_usage_gate

Recurrence metadata only plus usage gate.

Acceptance:
- `commands_succeeded`: `True`
- `read_only_verified`: `True`
- `grounding_score_remains_1`: `True`
- `hallucinations_remain_0`: `True`
- `confidence_calibration_not_regress`: `True`
- `planning_score_not_regress`: `True`
- `retrieval_recall_not_regress`: `True`
- `expected_outside_top10_not_regress`: `True`
- `expected_outside_top20_not_regress`: `True`
- `mean_expected_rank_improves`: `False`
- `mean_noise_above_expected_improves`: `False`
- `no_expected_top10_pushed_out`: `True`
- `noise_used_in_reasoning_not_increase`: `True`
- `reasoning_drift_cases_not_increase`: `True`
- `attention_precision_not_materially_regress`: `True`
- `attention_recall_not_materially_regress`: `True`
- `planning_core_coverage_not_regress`: `True`
- `response_core_coverage_not_regress`: `True`
- `sparse_behavior_not_regress`: `True`

Per-case changes:

| Case | Noise | Attention Precision | Decision | Planning Core | Response Core |
| --- | --- | --- | --- | --- | --- |
| planning_failed_assumption | `0 -> 0` | `1.0 -> 1.0` | `Under-Attending -> Under-Attending` | `0.6667 -> 0.6667` | `0.6667 -> 0.6667` |
| causal_industrial_failure | `6 -> 6` | `0.25 -> 0.25` | `Reasoning Drift -> Reasoning Drift` | `0.6667 -> 0.6667` | `0.6667 -> 0.6667` |
| contradictory_evidence | `1 -> 1` | `0.0 -> 0.0` | `Reasoning Drift -> Reasoning Drift` | `0.0 -> 0.0` | `0.0 -> 0.0` |
| resource_allocation_shelters | `1 -> 1` | `0.0 -> 0.0` | `Reasoning Drift -> Reasoning Drift` | `0.0 -> 0.0` | `0.0 -> 0.0` |
| risk_uncertainty_planning | `1 -> 1` | `0.0 -> 0.0` | `Reasoning Drift -> Reasoning Drift` | `0.0 -> 0.0` | `0.0 -> 0.0` |
| policy_audit_conflict | `0 -> 0` | `1.0 -> 1.0` | `Planning Drift -> Planning Drift` | `0.3333 -> 0.3333` | `0.3333 -> 0.3333` |
| multi_step_failure_revision | `3 -> 3` | `0.25 -> 0.25` | `Reasoning Drift -> Reasoning Drift` | `0.3333 -> 0.3333` | `0.3333 -> 0.3333` |
| logistics_proxy_planning | `0 -> 0` | `1.0 -> 1.0` | `Under-Attending -> Under-Attending` | `0.3333 -> 0.3333` | `0.3333 -> 0.3333` |
| sparse_violin_tuning | `0 -> 0` | `1.0 -> 1.0` | `Healthy -> Healthy` | `1.0 -> 1.0` | `1.0 -> 1.0` |
| unsupported_recipe | `0 -> 0` | `1.0 -> 1.0` | `Healthy -> Healthy` | `1.0 -> 1.0` | `1.0 -> 1.0` |

## Replacement-Noise Analysis

Combined variants are evaluated specifically against the rejected activation-only failure: ranking gains are not sufficient if replacement noise enters reasoning.

## Usage-Gate Effectiveness Analysis

The accepted usage gate remains the live safety layer. Its effectiveness depends on implementation-available support signals, not evaluator labels.

## Activation-Ranking Gains Retained Or Lost

See variant table and acceptance criteria for mean expected rank, expected outside top-10/top-20, and mean noise above expected.

## Regression Risks

- Activation recurrence can still reshuffle replacement noise into attention.
- Metadata-only variants may be safe but too weak to change outcomes.
- Strong evidence-support metadata can make reasoning usage gates permissive.

## Revert/Keep Actions Performed

Activation recurrence remains environment-disabled by default. Accepted reasoning usage gate remains enabled. Raw outputs were preserved for every variant.

`KEEP_USAGE_GATE_ONLY_RUN_MORE_DIAGNOSTICS`
