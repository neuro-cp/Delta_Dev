# Runtime V1.3 Query Evidence Model B Live Prototype

Final decision: `ACCEPT_RUNTIME_V13_QUERY_EVIDENCE_MODEL_B`

Model B was implemented inside the existing default `citation_context` reasoning usage gate. Activation recurrence remains disabled by default. No learning, governance, storage, provider, candidate-store, or canonical behavior was changed.

## Metric Comparison

| Metric | V1.2 Baseline | Refined V1.3 Default | Model B Projection | Model B Live |
| --- | ---: | ---: | ---: | ---: |
| read_only_verified | `True` | `True` | `None` | `True` |
| grounding_score | `1.0` | `1.0` | `1.0` | `1.0` |
| hallucinations | `0.0` | `0.0` | `0` | `0.0` |
| confidence_calibration | `1.0` | `1.0` | `None` | `1.0` |
| planning_score | `1.0` | `1.0` | `None` | `1.0` |
| retrieval_precision | `0.16` | `0.16` | `None` | `0.16` |
| retrieval_recall | `0.5333` | `0.5333` | `None` | `0.5333` |
| attention_precision | `0.55` | `0.5833` | `0.5385` | `0.6333` |
| attention_recall | `0.4333` | `0.4333` | `1.0` | `0.4333` |
| noise_used_in_reasoning | `12.0` | `8.0` | `6` | `7.0` |
| reasoning_drift_cases | `5.0` | `5.0` | `3` | `4.0` |
| planning_drift_cases | `1.0` | `1.0` | `None` | `1.0` |
| response_drift_cases | `0.0` | `0.0` | `None` | `0.0` |
| working_memory_efficiency | `0.19` | `0.15` | `None` | `0.14` |
| planning_core_coverage | `0.4333` | `0.4333` | `1.0` | `0.4333` |
| response_core_coverage | `0.4333` | `0.4333` | `1.0` | `0.4333` |
| pass_rate | `0.0` | `0.0` | `None` | `0.0` |
| expected_outside_top_10 | `8` | `8` | `None` | `8` |
| expected_outside_top_20 | `6` | `6` | `None` | `6` |
| mean_expected_rank | `10` | `10` | `None` | `10` |
| mean_noise_above_expected | `9.7083` | `9.7083` | `None` | `9.7083` |

## Acceptance Gates

- `read_only_verified`: `True`
- `grounding_score_remains_1`: `True`
- `hallucinations_remain_0`: `True`
- `confidence_calibration_not_regress`: `True`
- `planning_score_not_regress`: `True`
- `noise_used_decreases_or_not_regress`: `True`
- `reasoning_drift_decreases_or_not_increase`: `True`
- `planning_drift_not_increase`: `True`
- `response_drift_not_increase`: `True`
- `planning_core_coverage_not_regress`: `True`
- `response_core_coverage_not_regress`: `True`
- `retrieval_recall_not_regress`: `True`
- `expected_outside_top10_not_regress`: `True`
- `expected_outside_top20_not_regress`: `True`
- `mean_expected_rank_not_materially_regress`: `True`
- `mean_noise_above_not_materially_regress`: `True`

## Interpretation

- Live Model B reduced `noise_used_in_reasoning` from `8.0` to `7.0` against the refined default.
- `reasoning_drift_cases` improved from `5.0` to `4.0`.
- Grounding, hallucination, confidence, planning, retrieval, and ranking metrics remained stable.
- The live result is slightly less aggressive than the simulation projection (`6`) but passed the benchmark gate without blocking the fixture suite.

## Raw Outputs

- `reports/runtime_v13_query_evidence_model_b_live_raw/runtime_v12_real_knowledge.json`
- `reports/runtime_v13_query_evidence_model_b_live_raw/runtime_v12_activation_ranking_diagnostic.json`

`ACCEPT_RUNTIME_V13_QUERY_EVIDENCE_MODEL_B`
