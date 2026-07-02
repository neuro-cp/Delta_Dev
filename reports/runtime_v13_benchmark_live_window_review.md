# Runtime V1.3 Benchmark / Live-Window Review

Generated: `2026-07-02T17:09:22`

Report-only review. No runtime behavior, defaults, benchmark fixtures, learning, storage, governance, or providers were modified.

Current accepted default: Model B contextualized corpus support + citation_context reasoning usage gate

Final recommendation: `CHECKPOINT_MODEL_B_STOP_RUNTIME_V13`

## Summary

Model B is a stable V1.3 local optimum under current live-safe signals.

## Mitigation Ladder Summary

- `stabilizer`: `PROCEED_DEEP_ACTIVATION_DIAGNOSTICS`
- `deep_activation`: `PROCEED_RELATION_AWARE_ACTIVATION_SIMULATION`
- `relation_aware_activation`: `PROCEED_QUERY_DECOMPOSITION_ACTIVATION_SIMULATION`
- `query_decomposition`: `RUN_MORE_DIAGNOSTICS`
- `evidence_stage_separation`: `RUN_MORE_DIAGNOSTICS`
- `reasoning_citation_gate_review`: `PROCEED_EVIDENCE_CONTEXTUALIZATION_IN_ACTIVATION_SIMULATION`
- `evidence_contextualization`: `RUN_MORE_DIAGNICS`
- `availability`: `None`
- `consolidation`: `RETURN_TO_ACTIVATION_ATTENTION_DIAGNOSTICS`

## Remaining Failed Cases

- `planning_failed_assumption`: decision `Under-Attending`, missed `1`, classes `{'benchmark_expected_but_planning_only': 1}`
- `causal_industrial_failure`: decision `Reasoning Drift`, missed `1`, classes `{'outside_reasonable_activation_window': 1}`
- `contradictory_evidence`: decision `Reasoning Drift`, missed `3`, classes `{'visible_but_not_safely_separable': 3}`
- `resource_allocation_shelters`: decision `Reasoning Drift`, missed `3`, classes `{'visible_but_not_safely_separable': 3}`
- `risk_uncertainty_planning`: decision `Reasoning Drift`, missed `3`, classes `{'live_usable_but_requires_new_signal': 1, 'unavailable_or_unfair_target': 1, 'visible_but_not_safely_separable': 1}`
- `policy_audit_conflict`: decision `Planning Drift`, missed `2`, classes `{'outside_reasonable_activation_window': 2}`
- `multi_step_failure_revision`: decision `Under-Attending`, missed `2`, classes `{'visible_but_not_safely_separable': 2}`
- `logistics_proxy_planning`: decision `Under-Attending`, missed `2`, classes `{'visible_but_not_safely_separable': 2}`

## Missed Expected Concept Classification Table

| Case | Rank | Classification | Best Recovery Path | Counts Against V1.3 | Why Recovery Failed |
| --- | ---: | --- | --- | --- | --- |
| `planning_failed_assumption` | `3` | `benchmark_expected_but_planning_only` | `QDA visibility, ESS visibility, ESS planning support, ECA context strong, ECA projected gate admission` | `True` | Concept appears useful as planning support but not as citable reasoning/response evidence. |
| `causal_industrial_failure` | `37` | `outside_reasonable_activation_window` | `QDA visibility, ESS visibility` | `False` | Concept is present but low-ranked (rank 37), outside the practical V1.3 activation window. |
| `contradictory_evidence` | `7` | `visible_but_not_safely_separable` | `QDA visibility, ESS visibility` | `True` | The concept becomes visible, but all attempted live-safe recovery paths also expose same-topic noise. |
| `contradictory_evidence` | `2` | `visible_but_not_safely_separable` | `QDA visibility, ESS visibility, ECA context strong, ECA projected gate admission` | `True` | The concept becomes visible, but all attempted live-safe recovery paths also expose same-topic noise. |
| `contradictory_evidence` | `3` | `visible_but_not_safely_separable` | `QDA visibility, ESS visibility, ECA context strong, ECA projected gate admission` | `True` | The concept becomes visible, but all attempted live-safe recovery paths also expose same-topic noise. |
| `resource_allocation_shelters` | `11` | `visible_but_not_safely_separable` | `QDA visibility, ESS visibility, ECA context strong, ECA projected gate admission` | `True` | The concept becomes visible, but all attempted live-safe recovery paths also expose same-topic noise. |
| `resource_allocation_shelters` | `18` | `visible_but_not_safely_separable` | `QDA visibility, ESS visibility, ECA context strong, ECA projected gate admission` | `True` | The concept becomes visible, but all attempted live-safe recovery paths also expose same-topic noise. |
| `resource_allocation_shelters` | `1` | `visible_but_not_safely_separable` | `QDA visibility, ESS visibility, ECA context strong, ECA projected gate admission` | `True` | The concept becomes visible, but all attempted live-safe recovery paths also expose same-topic noise. |
| `risk_uncertainty_planning` | `2` | `live_usable_but_requires_new_signal` | `none` | `True` | Concept is in the top-20 but not made usable by current activation/attention/citation signals. |
| `risk_uncertainty_planning` | `None` | `unavailable_or_unfair_target` | `none` | `False` | Concept is absent from the diagnostic top-50 live window. |
| `risk_uncertainty_planning` | `4` | `visible_but_not_safely_separable` | `QDA visibility, ESS visibility` | `True` | The concept becomes visible, but all attempted live-safe recovery paths also expose same-topic noise. |
| `policy_audit_conflict` | `37` | `outside_reasonable_activation_window` | `QDA visibility, ESS visibility` | `False` | Concept is present but low-ranked (rank 37), outside the practical V1.3 activation window. |
| `policy_audit_conflict` | `22` | `outside_reasonable_activation_window` | `QDA visibility, ESS visibility` | `False` | Concept is present but low-ranked (rank 22), outside the practical V1.3 activation window. |
| `multi_step_failure_revision` | `6` | `visible_but_not_safely_separable` | `QDA visibility, ESS visibility` | `True` | The concept becomes visible, but all attempted live-safe recovery paths also expose same-topic noise. |
| `multi_step_failure_revision` | `40` | `visible_but_not_safely_separable` | `QDA visibility, ESS visibility` | `True` | The concept becomes visible, but all attempted live-safe recovery paths also expose same-topic noise. |
| `logistics_proxy_planning` | `4` | `visible_but_not_safely_separable` | `QDA visibility, ESS visibility, ECA context strong, ECA projected gate admission` | `True` | The concept becomes visible, but all attempted live-safe recovery paths also expose same-topic noise. |
| `logistics_proxy_planning` | `24` | `visible_but_not_safely_separable` | `QDA visibility, ESS visibility, ECA context strong, ECA projected gate admission` | `True` | The concept becomes visible, but all attempted live-safe recovery paths also expose same-topic noise. |

## Live-Usability Analysis

- Concepts that should count against Runtime V1.3: `13`
- Concepts requiring new live signal: `1`
- Known limitations or artifacts: `16`

## Inseparable Same-Topic Noise Analysis

- `visible_but_not_safely_separable`: `11`

## Benchmark/Live-Window Artifact Analysis

- `outside_reasonable_activation_window`: `3`
- `benchmark_expected_but_not_live_citable`: `0`
- `benchmark_expected_but_planning_only`: `1`
- `benchmark_expected_redundant_with_used_evidence`: `0`
- `unavailable_or_unfair_target`: `1`

## Whether Model B Is A Stable V1.3 Local Optimum

`True`

## Recommended Final V1.3 Disposition

Model B is a stable V1.3 local optimum under current live-safe signals.

## Continuation Checkpoint

- Model B default remains active: `True`
- Runtime files modified: `False`

CHECKPOINT_MODEL_B_STOP_RUNTIME_V13
