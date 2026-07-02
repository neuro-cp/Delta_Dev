# Runtime V1.3 Evidence Stage Separation Diagnostic

Generated: `2026-07-02T14:41:42`

Report-only diagnostic. No runtime behavior, learning, validation, normalization, governance, storage, providers, candidate stores, canonical systems, benchmark fixtures, or default behavior was modified.

Current accepted default: Model B contextualized corpus support + citation_context reasoning usage gate

Final recommendation: `RUN_MORE_DIAGNOSTICS`

## Summary

This diagnostic projected QDA-style visibility into separate lanes: `visible_only`, `citable_reasoning`, `planning_support`, and `excluded_noise`.

## Why QDA Failed

QDA ended with `RUN_MORE_DIAGNOSTICS`. QDA improved visibility, but either admitted reasoning noise or starved planning.

## Stage-Separation Models Tested

- `ESS1`: QDA visibility with Model B citable reasoning only.
- `ESS2`: non-citable planning support.
- `ESS3`: strict max-one planning support.
- `ESS4`: planning starvation guard.
- `ESS5`: dual-lane reasoning/planning evidence.
- `ESS6`: conservative hybrid.

## Model Comparison

| Model | Pass | Visible Exp | Visible Noise | Reason Exp | Reason Noise | Plan Support Exp | Plan Support Noise | Reasoning Drift | Planning Drift | Plan Cov | Resp Cov | Improved | Regressed |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ESS1 | `False` | `21` | `58` | `6` | `6` | `0` | `0` | `4` | `3` | `0.4` | `0.4` | `0` | `2` |
| ESS2 | `False` | `21` | `58` | `6` | `6` | `1` | `8` | `4` | `2` | `0.4333` | `0.4` | `1` | `1` |
| ESS3 | `False` | `21` | `58` | `6` | `6` | `1` | `3` | `4` | `2` | `0.4333` | `0.4` | `1` | `1` |
| ESS4 | `False` | `21` | `58` | `6` | `6` | `0` | `0` | `4` | `3` | `0.4` | `0.4` | `0` | `2` |
| ESS5 | `False` | `21` | `58` | `6` | `6` | `1` | `8` | `4` | `2` | `0.4333` | `0.4` | `1` | `1` |
| ESS6 | `False` | `21` | `58` | `6` | `6` | `1` | `3` | `4` | `2` | `0.4333` | `0.4` | `1` | `1` |

## Lane Assignment Examples

- `planning_failed_assumption`: {'citable_reasoning': 2, 'planning_support': 1, 'visible_only': 7}
- `causal_industrial_failure`: {'citable_reasoning': 5, 'visible_only': 4, 'planning_support': 1}
- `contradictory_evidence`: {'visible_only': 9, 'citable_reasoning': 1}
- `resource_allocation_shelters`: {'visible_only': 8, 'planning_support': 1, 'citable_reasoning': 1}
- `risk_uncertainty_planning`: {'citable_reasoning': 1, 'visible_only': 9}

## Case-Level Improvements/Regressions

### ESS1
- `planning_failed_assumption`: `Under-Attending` -> `Planning Drift`; planning support expected `0`, planning support noise `0`, reasoning noise `0`
- `multi_step_failure_revision`: `Under-Attending` -> `Planning Drift`; planning support expected `0`, planning support noise `0`, reasoning noise `0`

### ESS2
- `planning_failed_assumption`: `Under-Attending` -> `Healthy`; planning support expected `1`, planning support noise `1`, reasoning noise `0`
- `multi_step_failure_revision`: `Under-Attending` -> `Planning Drift`; planning support expected `0`, planning support noise `3`, reasoning noise `0`

### ESS3
- `planning_failed_assumption`: `Under-Attending` -> `Healthy`; planning support expected `1`, planning support noise `0`, reasoning noise `0`
- `multi_step_failure_revision`: `Under-Attending` -> `Planning Drift`; planning support expected `0`, planning support noise `1`, reasoning noise `0`

### ESS4
- `planning_failed_assumption`: `Under-Attending` -> `Planning Drift`; planning support expected `0`, planning support noise `0`, reasoning noise `0`
- `multi_step_failure_revision`: `Under-Attending` -> `Planning Drift`; planning support expected `0`, planning support noise `0`, reasoning noise `0`

### ESS5
- `planning_failed_assumption`: `Under-Attending` -> `Healthy`; planning support expected `1`, planning support noise `1`, reasoning noise `0`
- `multi_step_failure_revision`: `Under-Attending` -> `Planning Drift`; planning support expected `0`, planning support noise `3`, reasoning noise `0`

### ESS6
- `planning_failed_assumption`: `Under-Attending` -> `Healthy`; planning support expected `1`, planning support noise `0`, reasoning noise `0`
- `multi_step_failure_revision`: `Under-Attending` -> `Planning Drift`; planning support expected `0`, planning support noise `1`, reasoning noise `0`

## Planning Starvation Analysis

Planning starvation is indicated by planning drift increases or planning coverage below Model B while reasoning noise remains controlled.

## Reasoning-Noise Analysis

Reasoning noise is measured only in the citable reasoning lane. Planning-support noise is reported separately and does not alter reasoning/citation metrics.

## Sparse/Unsupported Safety

Sparse and unsupported cases remained guarded by question-text cues only and are included in every acceptance gate.

## Best Candidate

Passed candidates: `none`

## Rejected Candidates

- `ESS1` rejected: planning_drift_no_increase, planning_core_no_regress, response_core_no_regress, improves_failed_case
- `ESS2` rejected: planning_drift_no_increase, response_core_no_regress
- `ESS3` rejected: planning_drift_no_increase, response_core_no_regress
- `ESS4` rejected: planning_drift_no_increase, planning_core_no_regress, response_core_no_regress, improves_failed_case
- `ESS5` rejected: planning_drift_no_increase, response_core_no_regress
- `ESS6` rejected: planning_drift_no_increase, response_core_no_regress

## Live Prototype

Should be attempted later: `False`

## Continuation Checkpoint

- Model B default remains active: `True`
- Runtime files modified: `False`
- Raw archive: `G:\Delta_Dev\reports\runtime_v13_evidence_stage_separation_raw`

RUN_MORE_DIAGNOSTICS
