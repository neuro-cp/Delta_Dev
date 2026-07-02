# Runtime V1.3 Model B Challenge Suite

Generated: `2026-07-02T17:18:22`

Report-only challenge suite. No runtime behavior, defaults, learning, governance, storage, provider prompts, candidate stores, canonical storage, or benchmark fixtures were modified.

Current accepted default: Model B contextualized corpus support + citation_context reasoning usage gate

Final recommendation: `CHECKPOINT_MODEL_B_STOP_RUNTIME_V13`

## Summary

Ten conservative Model B-adjacent variants were evaluated. No variant is accepted unless it beats Model B without any hard-gate tradeoff.

## Why This Challenge Suite Was Run

User requested one final bounded Model B-adjacent challenge despite prior stop recommendation.

## Baseline Model B Metrics

- `grounding_score`: `1.0`
- `hallucinations`: `0.0`
- `confidence_calibration`: `1.0`
- `planning_score`: `1.0`
- `response_drift_cases`: `0.0`
- `noise_used_in_reasoning`: `7.0`
- `reasoning_drift_cases`: `4.0`
- `planning_drift_cases`: `1.0`
- `planning_core_coverage`: `0.4333`
- `response_core_coverage`: `0.4333`
- `attention_precision`: `0.6333`
- `attention_recall`: `0.4333`

## Harness Control Result From MBV10

- Matches Model B baseline: `True`

## 10-Variant Comparison Table

| Variant | Pass | Beats Model B | Noise | Reason Drift | Plan Drift | Plan Cov | Resp Cov | Improved | Regressed | Reason |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `MBV1` | `False` | `False` | `7.0` | `4.0` | `1.0` | `0.4333` | `0.4333` | `0.0` | `0.0` | failed: improves_case |
| `MBV2` | `False` | `False` | `1.0` | `1.0` | `1.0` | `0.3667` | `0.3667` | `3.0` | `0.0` | failed: planning_core_coverage, response_core_coverage |
| `MBV3` | `False` | `False` | `7.0` | `4.0` | `1.0` | `0.4333` | `0.4333` | `0.0` | `0.0` | failed: improves_case |
| `MBV4` | `False` | `False` | `7.0` | `4.0` | `1.0` | `0.4333` | `0.4333` | `0.0` | `0.0` | failed: improves_case |
| `MBV5` | `False` | `False` | `7.0` | `4.0` | `1.0` | `0.4333` | `0.4333` | `0.0` | `0.0` | failed: improves_case |
| `MBV6` | `False` | `False` | `1.0` | `1.0` | `2.0` | `0.4333` | `0.3667` | `3.0` | `0.0` | failed: planning_drift_cases, response_core_coverage |
| `MBV7` | `False` | `False` | `6.0` | `4.0` | `1.0` | `0.3667` | `0.4333` | `0.0` | `0.0` | failed: planning_core_coverage, improves_case |
| `MBV8` | `False` | `False` | `7.0` | `4.0` | `1.0` | `0.4333` | `0.4333` | `0.0` | `0.0` | failed: improves_case |
| `MBV9` | `False` | `False` | `6.0` | `4.0` | `1.0` | `0.4333` | `0.4333` | `0.0` | `0.0` | failed: improves_case |
| `MBV10` | `True` | `False` | `7.0` | `4.0` | `1.0` | `0.4333` | `0.4333` | `0.0` | `0.0` | passed all hard gates |

## Case-Level Improvements/Regressions

### MBV2
- `causal_industrial_failure`: `Reasoning Drift` -> `Under-Attending`
- `contradictory_evidence`: `Reasoning Drift` -> `Under-Attending`
- `risk_uncertainty_planning`: `Reasoning Drift` -> `Under-Attending`

### MBV6
- `causal_industrial_failure`: `Reasoning Drift` -> `Planning Drift`
- `contradictory_evidence`: `Reasoning Drift` -> `Under-Attending`
- `risk_uncertainty_planning`: `Reasoning Drift` -> `Under-Attending`

## Noise/Drift Analysis

Variants that reduce reasoning use by stricter filtering risk response/planning starvation. Variants that preserve coverage generally reproduce Model B.

## Sparse/Unsupported Safety

Sparse and unsupported safety remained part of every hard gate.

## Whether Any Variant Safely Beats Model B

`False`

## Final Recommendation

Best variant: `none`

## Continuation Checkpoint

- Model B default remains active: `True`
- Runtime files modified: `False`
- Raw archive: `G:\Delta_Dev\reports\runtime_v13_model_b_challenge_suite_raw`

CHECKPOINT_MODEL_B_STOP_RUNTIME_V13
