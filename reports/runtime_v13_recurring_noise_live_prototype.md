# Runtime V1.3 Recurring-Noise Live Prototype

Final decision: `REJECT_LIVE_RECURRING_NOISE_SUPPRESSION`

Ranking metrics improved, but noise_used_in_reasoning increased from 12 to 24 and attention precision regressed from 0.55 to 0.4172. The live patch violates acceptance criteria and must be reverted.

## Metrics

| Metric | V1.2 Baseline | V1.3 Prototype |
| --- | ---: | ---: |
| read_only_verified | `True` | `True` |
| grounding_score | `1.0` | `1.0` |
| hallucinations | `0.0` | `0.0` |
| confidence_calibration | `1.0` | `1.0` |
| planning_score | `1.0` | `1.0` |
| retrieval_precision | `0.16` | `0.17` |
| retrieval_recall | `0.5333` | `0.5667` |
| attention_precision | `0.55` | `0.4172` |
| attention_recall | `0.4333` | `0.4667` |
| noise_used_in_reasoning | `12.0` | `24.0` |
| expected_outside_top10 | `8` | `7` |
| expected_outside_top20 | `6` | `4` |
| mean_expected_rank | `10` | `7.1739` |
| mean_noise_above_expected | `9.7083` | `7` |

## Acceptance Criteria

| Criterion | Passed |
| --- | --- |
| grounding_score_remains_1 | `True` |
| hallucinations_remain_0 | `True` |
| confidence_calibration_not_regress | `True` |
| planning_score_not_regress | `True` |
| read_only_verified | `True` |
| expected_outside_top10_not_worse | `True` |
| expected_outside_top20_not_worse | `True` |
| mean_expected_rank_improves | `True` |
| mean_noise_above_expected_improves | `True` |
| no_expected_top10_pushed_out | `True` |
| noise_used_in_reasoning_not_increase | `False` |

## Expected Top-10 Concepts Pushed Out

- none

## Report Preservation

- V1.2 baseline reports were restored to `reports/runtime_v12_*`.
- Rejected live prototype raw benchmark outputs are archived in `reports/runtime_v13_recurring_noise_live_raw`.

## Action

The live runtime patch is rejected. Revert the recurring-noise suppression code while preserving this report and the benchmark outputs as evidence.

`REJECT_LIVE_RECURRING_NOISE_SUPPRESSION`
