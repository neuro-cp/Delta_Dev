# Runtime V1.3 Model B / MBV2 Hybrid Test

Generated: `2026-07-02T17:22:43`

Report-only hybrid test. No runtime behavior, defaults, learning, governance, storage, provider prompts, candidate stores, canonical storage, or benchmark fixtures were modified.

Current accepted default: Model B contextualized corpus support + citation_context reasoning usage gate

Final recommendation: `PROCEED_MODEL_B_MBV2_HYBRID_DORMANT_PROTOTYPE`

## Summary

The suite tested whether MBV2's useful stricter reasoning filter can be applied without accepting MBV2's planning/response coverage regression.

## Model B Baseline

- `attention_precision`: `0.6333`
- `attention_recall`: `0.4333`
- `confidence_calibration`: `1.0`
- `grounding_score`: `1.0`
- `hallucinations`: `0.0`
- `noise_used_in_reasoning`: `7.0`
- `planning_core_coverage`: `0.4333`
- `planning_drift_cases`: `1.0`
- `planning_score`: `1.0`
- `reasoning_drift_cases`: `4.0`
- `response_core_coverage`: `0.4333`
- `response_drift_cases`: `0.0`

## MBV2 Partial Signal Summary

- `noise_used_in_reasoning`: `7 -> 1`
- `citable_noise_used_in_reasoning`: `7 -> 1`
- `reasoning_drift_cases`: `4 -> 1`
- `improved_cases`: `3`

## Why MBV2 Failed

planning_core_coverage and response_core_coverage regressed from 0.4333 to 0.3667.

## Hybrid Comparison Table

| Hybrid | Pass | Safely Beats Model B | Noise | Reason Drift | Plan Drift | Plan Cov | Resp Cov | Improved | Regressed | Inconsistent | Reason |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `HYB1` | `True` | `True` | `5.0` | `2.0` | `1.0` | `0.4333` | `0.4333` | `2.0` | `0.0` | `0.0` | passed all hard gates |
| `HYB2` | `True` | `True` | `5.0` | `2.0` | `1.0` | `0.4333` | `0.4333` | `2.0` | `0.0` | `0.0` | passed all hard gates |
| `HYB3` | `False` | `False` | `1.0` | `1.0` | `2.0` | `0.4333` | `0.4333` | `3.0` | `0.0` | `3.0` | failed: planning_drift_cases, consistent_reasoning_planning_response |
| `HYB4` | `True` | `True` | `5.0` | `2.0` | `1.0` | `0.4333` | `0.4333` | `2.0` | `0.0` | `0.0` | passed all hard gates |
| `HYB5` | `True` | `True` | `5.0` | `2.0` | `1.0` | `0.4333` | `0.4333` | `2.0` | `0.0` | `0.0` | passed all hard gates |

## Case-Level Improvements/Regressions

### HYB1
- `contradictory_evidence`: `Reasoning Drift` -> `Under-Attending`
- `risk_uncertainty_planning`: `Reasoning Drift` -> `Under-Attending`

### HYB2
- `contradictory_evidence`: `Reasoning Drift` -> `Under-Attending`
- `risk_uncertainty_planning`: `Reasoning Drift` -> `Under-Attending`

### HYB3
- `causal_industrial_failure`: `Reasoning Drift` -> `Planning Drift`
- `contradictory_evidence`: `Reasoning Drift` -> `Under-Attending`
- `risk_uncertainty_planning`: `Reasoning Drift` -> `Under-Attending`

### HYB4
- `contradictory_evidence`: `Reasoning Drift` -> `Under-Attending`
- `risk_uncertainty_planning`: `Reasoning Drift` -> `Under-Attending`

### HYB5
- `contradictory_evidence`: `Reasoning Drift` -> `Under-Attending`
- `risk_uncertainty_planning`: `Reasoning Drift` -> `Under-Attending`

## Coverage Preservation Analysis

Hybrids with full coverage fallback preserve baseline coverage but reproduce Model B and improve zero cases. Reasoning-only filtering creates inconsistent reasoning/planning/response state.

## Noise/Drift Analysis

Noise reduction is achievable only when evidence is removed from reasoning; preserving planning/response coverage either falls back to Model B or creates inconsistency.

## Whether Any Hybrid Safely Beats Model B

`True`

## Final Recommendation

Best hybrid: `HYB1`

## Continuation Checkpoint

- Model B default remains active: `True`
- Runtime files modified: `False`
- Raw archive: `G:\Delta_Dev\reports\runtime_v13_model_b_mbv2_hybrid_raw`

PROCEED_MODEL_B_MBV2_HYBRID_DORMANT_PROTOTYPE
