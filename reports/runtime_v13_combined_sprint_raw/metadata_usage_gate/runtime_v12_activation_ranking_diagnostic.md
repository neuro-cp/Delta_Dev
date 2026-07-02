# Runtime V1.2 Activation Ranking Diagnostic

- campaign: `.tmp\experiments\phaseA_architecture_graduation\overnight_3000`
- read-only verified: `True`
- baseline limit: `10`
- diagnostic limit: `50`

## Aggregate

| Metric | Value |
| --- | ---: |
| mean_expected_rank | `10` |
| median_expected_rank | `3` |
| expected_outside_top_10 | `8` |
| expected_outside_top_20 | `6` |
| mean_noise_above_expected | `9.7083` |
| attention_secondary_to_activation_cases | `3` |
| attention_primary_cases | `3` |
| mixed_activation_attention_cases | `2` |
| sparse_activation_abstention_cases | `2` |

## Top Recurring Noisy Concepts

| Concept ID | Count |
| --- | ---: |
| `e0038487-2363-4ba8-8e2e-a1b465c44ee0` | `8` |
| `5252e50d-b97e-4d57-a79a-b9d64ddbbec7` | `8` |
| `5ac48263-cbff-4380-bf63-fc9500bcad8d` | `8` |
| `0586e881-099d-4866-a1cf-4ed571139c70` | `8` |
| `cb4f7649-cbdd-4cb3-905d-6f5f69832e9c` | `7` |
| `06b4d255-58d5-49f5-adec-43426ce0d09b` | `7` |
| `65e4ca55-7169-4ee4-b388-a6927043a92d` | `6` |
| `17a8d30a-9f2d-4d15-8100-d4bf18ca2e71` | `6` |
| `89b85467-0655-47d3-9a0c-89da364cd487` | `6` |
| `b85b0a01-9c3f-4c42-a26a-01741c84682c` | `6` |

## Top Recurring Lexical Attractors

| Token | Count |
| --- | ---: |
| `resource` | `23` |
| `evidence` | `21` |
| `emergency` | `20` |
| `failure` | `20` |
| `uncertainty` | `14` |
| `plan` | `13` |
| `risk` | `10` |
| `response` | `5` |
| `change` | `2` |
| `capacity` | `2` |

## Case Summary

| Case | Diagnosis | Expected Outside Top 10 | Pruned By Attention | Sparse Noise |
| --- | --- | ---: | ---: | ---: |
| planning_failed_assumption | `attention_primary` | `0` | `1` | `0` |
| causal_industrial_failure | `activation_ranking_primary` | `1` | `0` | `0` |
| contradictory_evidence | `attention_primary` | `0` | `3` | `0` |
| resource_allocation_shelters | `activation_ranking_primary` | `2` | `1` | `0` |
| risk_uncertainty_planning | `attention_primary` | `1` | `2` | `0` |
| policy_audit_conflict | `activation_ranking_primary` | `2` | `0` | `0` |
| multi_step_failure_revision | `mixed_activation_attention` | `1` | `1` | `0` |
| logistics_proxy_planning | `mixed_activation_attention` | `1` | `1` | `0` |
| sparse_violin_tuning | `sparse_activation_abstention_needed` | `0` | `0` | `50` |
| unsupported_recipe | `sparse_activation_abstention_needed` | `0` | `0` | `50` |

## Recommended Runtime V1.3 intervention candidates

- Activation ranking diagnostic/prototype: relevant concepts frequently rank outside the top-10 working window.
- Attention scoring diagnostic/prototype: some cases retrieve expected concepts in the top-10 but prune them before working memory.
- Sparse-query abstention gate: unsupported questions activate unrelated concepts before attention suppresses them.

## Rejected intervention candidates

- Do not modify learning, validation, normalization, governance, promotion scoring, or provider prompts.
- Do not loosen attention or promotion thresholds based only on aggregate V1.2 metrics.
- Do not begin conversation support until real-store single-turn activation is more reliable.

## Evidence required before implementation

- Any future change must improve Runtime V1.2 real-store metrics while preserving grounding=1.0, hallucinations=0, read-only store hashes, and sparse refusal behavior.
- Compare against reports/runtime_v12_real_knowledge.json and reports/runtime_v12_activation_ranking_diagnostic.json before accepting changes.

## Benchmark command to run before and after any future change

- .\.venv311\Scripts\python.exe tools\runtime_v12_real_knowledge.py --campaign-root .tmp\experiments\phaseA_architecture_graduation --campaign overnight_3000 --reports-dir reports
- .\.venv311\Scripts\python.exe tools\runtime_v12_activation_ranking_diagnostic.py --campaign-root .tmp\experiments\phaseA_architecture_graduation --campaign overnight_3000 --reports-dir reports
