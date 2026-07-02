# Runtime V1.3 Reasoning Usage-Gate Simulation

Final recommendation: `PROCEED_REASONING_USAGE_GATE_LIVE_PROTOTYPE`

## Baseline vs Rejected Prototype vs Simulated Usage-Gate Metrics

| Metric | Baseline | Rejected Prototype | Simulated Usage Gate |
| --- | ---: | ---: | ---: |
| noise_used_in_reasoning | `12.0` | `24.0` | `12` |
| attention_precision | `0.55` | `0.4172` | `0.4172` |
| attention_recall | `0.4333` | `0.4667` | `0.4667` |
| reasoning_drift_cases | `5.0` | `8.0` | `5` |
| planning_core_coverage | `0.4333` | `0.4667` | `0.4667` |
| response_core_coverage | `0.4333` | `0.4667` | `0.4667` |
| grounding_score | `1.0` | `1.0` | `1.0` |
| hallucinations | `0.0` | `0.0` | `0.0` |

## Per-Case Gate Results

| Case | Noise Before | Noise After | Blocked New Noise | Expected Blocked | Useful Blocked | Projected Drift |
| --- | ---: | ---: | --- | --- | --- | --- |
| planning_failed_assumption | `1` | `0` | `1` | `0` | `0` | `False` |
| causal_industrial_failure | `7` | `6` | `1` | `0` | `0` | `True` |
| contradictory_evidence | `2` | `1` | `1` | `0` | `0` | `True` |
| resource_allocation_shelters | `1` | `1` | `0` | `0` | `0` | `True` |
| risk_uncertainty_planning | `8` | `1` | `7` | `0` | `0` | `True` |
| policy_audit_conflict | `1` | `0` | `1` | `0` | `0` | `False` |
| multi_step_failure_revision | `3` | `3` | `0` | `0` | `0` | `True` |
| logistics_proxy_planning | `1` | `0` | `1` | `0` | `0` | `False` |
| sparse_violin_tuning | `0` | `0` | `0` | `0` | `0` | `False` |
| unsupported_recipe | `0` | `0` | `0` | `0` | `0` | `False` |

## Gate Coverage

- total newly used noise concepts: `12`
- newly used noise blocked: `12`
- newly used noise not blocked: `0`
- expected/useful concepts blocked: `0`
- blocked noise ratio: `1.0`

## Risk Analysis

- cases where gate helps: `planning_failed_assumption, causal_industrial_failure, contradictory_evidence, risk_uncertainty_planning, policy_audit_conflict, logistics_proxy_planning`
- cases where gate is risky: `none`
- risk_uncertainty_planning: improves without suppressing expected concepts
- planning_failed_assumption: expected evidence remains usable

## Implementation Boundary

Safe future live signals:
- `attention_classification`
- `attention_score`
- `activation_rank`
- `activation_score`
- `query_overlap_terms`
- `specific_overlap_count`
- `entered_activation_top10`
- `recurrence_or_replacement_risk_metadata`
- `evidence_support_if_available`
- `centrality/promotion/confidence if already present in candidate metadata`

Evaluation-only labels that must not be used live:
- `Noise`
- `Core`
- `expected concept`
- `useful neighbor`
- `human/evaluator correctness labels`

## Acceptance Criteria

- `noise_used_in_reasoning_decreases_materially`: `True`
- `no_expected_concepts_blocked`: `True`
- `no_useful_neighbors_blocked`: `True`
- `grounding_score_stable`: `True`
- `hallucinations_stable`: `True`
- `reasoning_drift_not_worse`: `True`
- `reasoning_drift_decreases`: `True`
- `planning_core_coverage_not_regress`: `True`
- `response_core_coverage_not_regress`: `True`

## Recommendation

Proceed to a live prototype only if it preserves the simulation boundary: keep activation and attention visible, gate reasoning usage, and add regression checks for expected concepts in risk_uncertainty_planning.

`PROCEED_REASONING_USAGE_GATE_LIVE_PROTOTYPE`
