# Runtime V1.3 HYB1 Dormant Prototype Validation

Generated: `2026-07-02T17:29:20`

Current accepted default: Model B contextualized corpus support + citation_context reasoning usage gate

Final recommendation: `KEEP_HYB1_DORMANT_PROTOTYPE`

## Summary

HYB1 is present only as a dormant, environment-gated projection selector. Model B remains the no-env runtime default.

## Default Parity

- no-env HYB1 enabled: `False`
- harness control: `MBV10`
- matches Model B baseline: `True`
- selector smoke passed: `True`
- default parity passed: `True`

## HYB1 Enabled Validation

- env flag: `DELTA_RUNTIME_V13_HYB1_ENABLED`
- selector saw HYB1 enabled: `True`
- archived projection match: `True`
- validation passed: `True`

| Metric | Value | Gate Passed |
| --- | ---: | --- |
| `noise_used_in_reasoning` | `5.0` | `True` |
| `citable_noise_used_in_reasoning` | `5.0` | `True` |
| `reasoning_drift_cases` | `2.0` | `True` |
| `planning_drift_cases` | `1.0` | `True` |
| `planning_core_coverage` | `0.4333` | `True` |
| `response_core_coverage` | `0.4333` | `True` |
| `response_drift_cases` | `0.0` | `True` |
| `cases_improved` | `2.0` | `True` |
| `cases_regressed` | `0.0` | `True` |
| `sparse_violin_tuning_safe` | `True` | `True` |
| `unsupported_recipe_safe` | `True` | `True` |
| `grounding_score` | `1.0` | `True` |
| `hallucinations` | `0.0` | `True` |
| `confidence_calibration` | `1.0` | `True` |
| `planning_score` | `1.0` | `True` |

## Final State

- Model B remains default.
- HYB1 remains dormant/env-gated.
- No learning, governance, storage, provider, candidate-store, canonical-store, or benchmark-fixture changes were made.

KEEP_HYB1_DORMANT_PROTOTYPE
