# Runtime V1.3 Reasoning Usage-Gate Live Prototype

Final decision: `ACCEPT_RUNTIME_V13_REASONING_USAGE_GATE`

The live usage gate is safe against the restored V1.2 baseline but dormant on this activation path; it did not improve or regress aggregate metrics because current baseline candidates carry sufficient runtime support metadata to pass the gate.

## Baseline vs Live Usage-Gate Prototype

| Metric | V1.2 Baseline | Live Usage Gate | Delta |
| --- | ---: | ---: | ---: |
| read_only_verified | `True` | `True` | `None` |
| grounding_score | `1.0` | `1.0` | `0.0` |
| hallucinations | `0.0` | `0.0` | `0.0` |
| confidence_calibration | `1.0` | `1.0` | `0.0` |
| planning_score | `1.0` | `1.0` | `0.0` |
| retrieval_precision | `0.16` | `0.16` | `0.0` |
| retrieval_recall | `0.5333` | `0.5333` | `0.0` |
| attention_precision | `0.55` | `0.55` | `0.0` |
| attention_recall | `0.4333` | `0.4333` | `0.0` |
| noise_used_in_reasoning | `12.0` | `12.0` | `0.0` |
| reasoning_drift_cases | `5.0` | `5.0` | `0.0` |
| planning_drift_cases | `1.0` | `1.0` | `0.0` |
| response_drift_cases | `0.0` | `0.0` | `0.0` |
| working_memory_efficiency | `0.19` | `0.19` | `0.0` |
| planning_core_coverage | `0.4333` | `0.4333` | `0.0` |
| response_core_coverage | `0.4333` | `0.4333` | `0.0` |
| expected_outside_top10 | `8` | `8` | `0` |
| expected_outside_top20 | `6` | `6` | `0` |
| mean_expected_rank | `10` | `10` | `0` |
| mean_noise_above_expected | `9.7083` | `9.7083` | `0.0` |

## Acceptance Criteria

- `read_only_verified_remains_true`: `True`
- `grounding_score_remains_1`: `True`
- `hallucinations_remain_0`: `True`
- `confidence_calibration_not_regress`: `True`
- `planning_score_not_regress`: `True`
- `noise_used_in_reasoning_not_increase`: `True`
- `reasoning_drift_cases_not_increase`: `True`
- `attention_recall_not_materially_regress`: `True`
- `planning_core_coverage_not_regress`: `True`
- `response_core_coverage_not_regress`: `True`
- `sparse_behavior_not_regress`: `True`

## Raw Outputs

- `reports/runtime_v13_reasoning_usage_gate_live_raw`

`ACCEPT_RUNTIME_V13_REASONING_USAGE_GATE`
