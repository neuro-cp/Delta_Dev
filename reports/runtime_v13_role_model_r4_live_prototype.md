# Runtime V1.3 Role Model R4 Live Prototype

## Decision

`ACCEPT_SAFE_ROLE_GUARD_DORMANT_ON_BASELINE`

Live-default R4 was tested and rejected as a default because it reduced citable noise but over-pruned evidence enough to regress planning. The final no-env runtime remains the accepted Model B baseline. R4 is retained as an opt-in guarded path for future revision and is covered by focused tests.

## Default Runtime State

- enabled: `citation_context` reasoning usage gate
- enabled: Query Evidence Model B contextualized corpus support
- disabled: activation recurrence
- disabled: Runtime V1.3 Role Model R4 unless `DELTA_RUNTIME_V13_ROLE_GATE_MODE=r4` is set

## Metric Comparison

| Metric | V1.2 Baseline | Model B Accepted | R4 Live Default Attempt | Final No-Env R4 Dormant |
| --- | ---: | ---: | ---: | ---: |
| read_only_verified | `True` | `True` | `None` | `True` |
| grounding_score | `1.0` | `1.0` | `1.0` | `1.0` |
| hallucinations | `0.0` | `0.0` | `0.0` | `0.0` |
| confidence_calibration | `1.0` | `1.0` | `None` | `1.0` |
| planning_score | `1.0` | `1.0` | `0.8` | `1.0` |
| retrieval_precision | `0.16` | `0.16` | `None` | `0.16` |
| retrieval_recall | `0.5333` | `0.5333` | `None` | `0.5333` |
| attention_precision | `0.55` | `0.6333` | `0.9` | `0.6333` |
| attention_recall | `0.4333` | `0.4333` | `0.4333` | `0.4333` |
| noise_used_in_reasoning | `12.0` | `7.0` | `1.0` | `7.0` |
| citable_noise_used_in_reasoning | `None` | `None` | `1.0` | `7.0` |
| reasoning_drift_cases | `5.0` | `4.0` | `1.0` | `4.0` |
| planning_drift_cases | `1.0` | `1.0` | `2.0` | `1.0` |
| response_drift_cases | `0.0` | `0.0` | `0.0` | `0.0` |
| working_memory_efficiency | `0.19` | `0.14` | `None` | `0.14` |
| planning_core_coverage | `0.4333` | `0.4333` | `0.4333` | `0.4333` |
| response_core_coverage | `0.4333` | `0.4333` | `0.4333` | `0.4333` |
| pass_rate | `0.0` | `0.0` | `None` | `0.0` |
| core_evidence_count | `None` | `None` | `8.0` | `14.0` |
| supporting_context_count | `None` | `None` | `5.0` | `0.0` |
| peripheral_context_count | `None` | `None` | `1.0` | `0.0` |
| non_evidence_count | `None` | `None` | `5.0` | `5.0` |

## Ranking Comparison

| Metric | V1.2 Baseline | Model B Accepted | Final No-Env R4 Dormant |
| --- | ---: | ---: | ---: |
| expected_outside_top_10 | `8` | `8` | `8` |
| expected_outside_top_20 | `6` | `6` | `6` |
| mean_expected_rank | `10` | `10` | `10` |
| mean_noise_above_expected | `9.7083` | `9.7083` | `9.7083` |
| median_expected_rank | `3` | `3` | `3` |

## Live-Default R4 Finding

- noise used in reasoning improved from `7.0` to `1.0` in the attempted live-default run.
- reasoning drift improved from `4.0` to `1.0`.
- attention precision improved from `0.6333` to `0.9`.
- planning score regressed from `1.0` to `0.8`.
- planning drift regressed from `1.0` to `2.0`.

Conclusion: R4 has a real protective signal, but it is too aggressive as a default because it turns some necessary citable evidence into non-citable context.

## Acceptance Checks On Final No-Env Default

### safety

| Check | Passed |
| --- | ---: |
| read_only_verified | `True` |
| grounding_score_1 | `True` |
| hallucinations_0 | `True` |
| confidence_no_regress | `True` |
| planning_score_no_regress | `True` |

### runtime_quality

| Check | Passed |
| --- | ---: |
| noise_no_regress | `True` |
| reasoning_drift_no_regress | `True` |
| planning_drift_no_regress | `True` |
| response_drift_no_regress | `True` |
| planning_core_no_regress | `True` |
| response_core_no_regress | `True` |

### retrieval_ranking

| Check | Passed |
| --- | ---: |
| retrieval_recall_no_regress | `True` |
| expected_outside_top10_no_regress | `True` |
| expected_outside_top20_no_regress | `True` |
| mean_expected_rank_no_material_regress | `True` |
| mean_noise_above_expected_no_material_regress | `True` |

## Files Changed

- `orchestration/runtime/runtime_reasoning.py`
- `orchestration/runtime/runtime_evaluation.py`
- `orchestration/tests/runtime/test_runtime_reasoning.py`
- `docs/UPDATE.md`
- `docs/continuation_runtime_v13_role_model_r4.md`

## Reports Generated

- `reports/runtime_v13_role_model_r4_live_prototype.md`
- `reports/runtime_v13_role_model_r4_live_prototype.json`
- `reports/runtime_v13_role_model_r4_live_raw/runtime_v12_real_knowledge.json`
- `reports/runtime_v13_role_model_r4_live_raw/runtime_v12_activation_ranking_diagnostic.json`

## Next Recommended Task

Do not enable R4 by default yet. The next work should revise the role model against the planning regressions, likely by distinguishing citable operational evidence from near-neighbor explanatory context. Keep Model B as the live default until an R4 variant reduces citable noise without planning regression.

ACCEPT_SAFE_ROLE_GUARD_DORMANT_ON_BASELINE
