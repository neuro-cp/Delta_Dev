# OV3/OV4 HYB1 Shadow Comparison

- mode: `shadow_report_only`
- exact_payload_match: `True`
- hyb1_effective_output_change: `False`
- model_b_default_changed: `False`
- hyb1_promoted: `False`
- final_recommendation: `KEEP_MODEL_B_DEFAULT_HYB1_SHADOW_PARITY_CONFIRMED`

## Workloads

### OV3

- baseline_hash: `40c988d33f7476e5`
- hyb1_shadow_hash: `40c988d33f7476e5`
- payloads_equal: `True`
- metric_deltas: `0`
- hyb1_projection_strategy: `hyb1_mbv2_coverage_safe`

Baseline metrics:

- reasoning_quality_score: 0.975
- reasoning_benchmark_average: 0.909
- reasoning_benchmark_pass_rate: 1.0
- activation_confidence: 0.585
- ov3_readiness_score: 0.865
- final_recommendation: PROCEED_OV4_OPERATOR_REVIEWED_READONLY_ACTIVATION_TRIAL

HYB1 shadow metrics:

- reasoning_quality_score: 0.975
- reasoning_benchmark_average: 0.909
- reasoning_benchmark_pass_rate: 1.0
- activation_confidence: 0.585
- ov3_readiness_score: 0.865
- final_recommendation: PROCEED_OV4_OPERATOR_REVIEWED_READONLY_ACTIVATION_TRIAL

### OV4

- baseline_hash: `16981cf62701f60a`
- hyb1_shadow_hash: `16981cf62701f60a`
- payloads_equal: `True`
- metric_deltas: `0`
- hyb1_projection_strategy: `hyb1_mbv2_coverage_safe`

Baseline metrics:

- activation_state: read_only_trial
- activation_confidence: 0.64
- activation_readiness: 0.909
- governance_confidence: 0.94
- safety_confidence: 1.0
- final_recommendation: PROCEED_OV5_READONLY_RETRIEVAL_SYNTHESIS_TRIAL

HYB1 shadow metrics:

- activation_state: read_only_trial
- activation_confidence: 0.64
- activation_readiness: 0.909
- governance_confidence: 0.94
- safety_confidence: 1.0
- final_recommendation: PROCEED_OV5_READONLY_RETRIEVAL_SYNTHESIS_TRIAL

## Interpretation

HYB1 shadow mode produced no OV3/OV4 output delta. That means the current OV3 and OV4 workloads preserve parity under the HYB1 shadow environment; HYB1 remains a dormant projection/shadow candidate and does not alter these operational-validation paths.
