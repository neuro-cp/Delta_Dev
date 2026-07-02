# Runtime V1.2 Activation Ranking Diagnostic

- campaign: `.tmp\experiments\phaseA_architecture_graduation\overnight_3000`
- read-only verified: `True`
- baseline limit: `10`
- diagnostic limit: `50`

## Aggregate

| Metric | Value |
| --- | ---: |
| mean_expected_rank | `7.1739` |
| median_expected_rank | `3` |
| expected_outside_top_10 | `7` |
| expected_outside_top_20 | `4` |
| mean_noise_above_expected | `7` |
| attention_secondary_to_activation_cases | `3` |
| attention_primary_cases | `3` |
| mixed_activation_attention_cases | `2` |
| sparse_activation_abstention_cases | `2` |

## Top Recurring Noisy Concepts

| Concept ID | Count |
| --- | ---: |
| `b887cc74-2628-4fbd-8890-38792ed54876` | `6` |
| `76120648-7522-4025-8176-5e5fb199c687` | `6` |
| `d9ba0c9f-f458-4512-a0e3-40892ef333b6` | `6` |
| `3a9f7658-b877-4532-b9c8-1a79b360c5d4` | `5` |
| `0ada7d73-b196-40cc-b6bb-031ac1eaa8cd` | `5` |
| `a61cdfc3-a845-4b83-94b6-cf93ff6b0a08` | `5` |
| `2ecb3022-1ce7-46e9-b1e5-4da1ffd0ac7d` | `5` |
| `7a4b823b-f9df-4e77-b3b7-744ee834741c` | `4` |
| `636f4a37-3296-4858-be5d-99d1988bc3d6` | `4` |
| `df85054d-ffcd-4c50-8118-ecb512271eaf` | `3` |

## Top Recurring Lexical Attractors

| Token | Count |
| --- | ---: |
| `resource` | `23` |
| `failure` | `22` |
| `emergency` | `18` |
| `uncertainty` | `18` |
| `evidence` | `13` |
| `plan` | `13` |
| `risk` | `10` |
| `response` | `3` |
| `change` | `2` |
| `capacity` | `2` |

## Case Summary

| Case | Diagnosis | Expected Outside Top 10 | Pruned By Attention | Sparse Noise |
| --- | --- | ---: | ---: | ---: |
| planning_failed_assumption | `attention_primary` | `0` | `2` | `0` |
| causal_industrial_failure | `activation_ranking_primary` | `1` | `0` | `0` |
| contradictory_evidence | `attention_primary` | `0` | `3` | `0` |
| resource_allocation_shelters | `attention_primary` | `1` | `2` | `0` |
| risk_uncertainty_planning | `activation_ranking_primary` | `1` | `0` | `0` |
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
