# Phase 22 Bottleneck Audit

## Scope

This audit reviewed the current promotion governance outputs after virtual semantic relationship projection.

Reports inspected:

- `reports/phase22_projection_comparison.json`
- `reports/promotion_governance_report.json`
- `reports/promotion_candidates.md`
- `reports/promotion_rejections.md`
- `reports/concept_lifecycle_report.md`
- `reports/phase17_validation_report.json`
- `reports/phase18_normalization_report.json`
- `reports/_phase22_projected/*/promotion_governance_report.json`

No code, runtime stores, canonical knowledge, or experiment data were modified.

## Phase 22 Result

Virtual semantic relationship projection did address the previous visibility bottleneck.

| Metric | Value |
|---|---:|
| Concepts evaluated | 237 |
| Average raw centrality | 0.0000 |
| Average projected centrality | 0.2904 |
| Average raw promotion score | 0.4899 |
| Average projected promotion score | 0.5184 |
| Average score delta | +0.0285 |
| Concepts boosted by projection | 189 |
| Recommendation changes | 29 |
| Promotion eligible concepts | 0 |

Conclusion: relationship visibility is no longer the dominant blocker. Projection changed governance recommendations and raised centrality, but did not create promotion-eligible concepts.

## Governance Distribution After Projection

| Recommendation | Count |
|---|---:|
| Candidate | 128 |
| Validated | 75 |
| Reject | 24 |
| Hold for More Validation | 10 |
| Promotion Eligible | 0 |

## Eligibility Blockers

Across all non-eligible projected concepts:

| Blocker | Count |
|---|---:|
| Score below 0.62 | 233 |
| Incomplete proposition | 94 |
| Redundancy above 0.22 | 90 |
| Prompt specificity above 0.16 | 54 |
| No supported prediction | 29 |
| Evidence support below 0.75 | 29 |
| Unresolved prediction | 28 |
| Open contradiction | 8 |
| Failed validation | 6 |

Among near-miss concepts with score >= 0.56:

| Blocker | Count |
|---|---:|
| Score below 0.62 | 122 |
| Redundancy above 0.22 | 52 |
| Incomplete proposition | 35 |
| Prompt specificity above 0.16 | 28 |

Among concepts already scoring above the promotion threshold of 0.62:

| Blocker | Count |
|---|---:|
| Prompt specificity above 0.16 | 3 |
| Incomplete proposition | 1 |

This means the gate is not merely too strict. The few concepts that score high enough are blocked for legitimate quality reasons.

## Provider Provenance

Prompt-shaped and incomplete concepts are strongly concentrated in Qwen outputs.

| Subset | Qwen | Unknown | Llama |
|---|---:|---:|---:|
| All artifact/incomplete concepts | 73 | 48 | 6 |
| Near-miss artifact/incomplete concepts | 46 | 3 | 2 |
| All near-miss concepts | 121 | 3 | 2 |

Repeated near-miss fragments also cluster under Qwen, including:

- `The cycle can be completed by predicting that`
- `For instance if a previous handoff was delayed`
- `If the large tent is allocated to one`
- `To predict a handoff failure status updates should`
- `Evidence that would revise the belief could include`

Conclusion: the artifact issue is not evenly distributed. In this projected governance set, Qwen dominates both near-miss concepts and near-miss artifacts.

## Prior Phase Context

Phase 17 showed validation and falsification are functioning:

| Metric | Value |
|---|---:|
| Prediction coverage after adversarial validation | 0.8068 |
| Supported predictions | 323 |
| Failed predictions | 57 |
| Outstanding predictions | 23 |
| Contradiction resolution rate | 0.6304 |

Phase 18 showed normalization has limited recovery power:

| Metric | Value |
|---|---:|
| Failed predictions considered | 40 |
| Normalized concepts | 36 |
| Recovered concepts | 3 |
| Normalization precision | 0.0833 |
| Still rejected | 33 |

Conclusion: remaining failures are mostly not superficial wording problems that conservative normalization can recover after the fact.

## Single Largest Remaining Bottleneck

The dominant bottleneck is semantic proposition quality at extraction time, especially incomplete, prompt-shaped, and duplicated fragments from Qwen-generated experiences.

The evidence does not support loosening promotion thresholds yet:

1. Projection already fixed the relationship visibility issue enough to raise average centrality from 0.0000 to 0.2904.
2. The only concepts above the promotion score threshold were blocked by prompt specificity or incomplete proposition checks.
3. Many concepts just below threshold also read as fragments despite not always being flagged as incomplete.
4. Phase 18 showed post-hoc normalization recovered only 3 concepts, so the better intervention point is extraction or provider-output filtering before governance.

## Recommendation

Do not lower promotion eligibility thresholds yet.

The next justified change should be a targeted refinement of the existing semantic extraction or governance quality gate:

- detect dangling conditionals such as `If ...` without a complete consequent;
- detect prompt/process scaffolding such as `The cycle can be completed by predicting that`;
- detect example-framing fragments such as `For instance if ...`;
- strengthen duplicate handling for repeated near-miss fragments;
- preserve provider provenance so Qwen-specific artifact pressure can be measured without provider-specific prompt tuning.

This is a change to an existing quality gate, not a new subsystem.

Success should be measured by rerunning the same projected governance audit and verifying:

- fewer high-scoring incomplete fragments;
- fewer Qwen-derived prompt artifacts;
- stable or higher validated concept count;
- no artificial increase in promotion eligibility from lowered standards;
- promotion eligibility only for complete reusable propositions.

## Implemented Refinement

The existing promotion governance quality gate was refined to treat the following as incomplete propositions:

- dangling `if` or `when` clauses without a consequent;
- example-framed conditionals such as `For instance if ...`;
- process scaffolding such as `The cycle can be completed by predicting that`;
- modal endings such as `should`, `must`, `will`, `can`, and incomplete forms of `be`.

This refinement does not rewrite concepts, infer missing meaning, lower thresholds, or make any concept easier to promote. It only prevents incomplete fragments from advancing through governance because projected centrality made them appear structurally stronger.

Focused tests passed:

- `orchestration/tests/runtime/test_promotion_governance.py`
- `orchestration/tests/runtime/test_phase22_projection_comparison.py`

Result: `17 passed`.

## Post-Refinement Projection Rerun

The Phase 22 projection comparison was rerun against the existing Phase 20 campaign stores only. No new learning, validation, canonical promotion, or provider inference was performed.

| Metric | Value |
|---|---:|
| Concepts evaluated | 237 |
| Average raw centrality | 0.0000 |
| Average projected centrality | 0.2904 |
| Average promotion score delta | +0.0285 |
| Recommendation changes | 13 |
| Promotion eligible concepts | 0 |

Post-refinement recommendation distribution:

| Recommendation | Count |
|---|---:|
| Candidate | 163 |
| Validated | 40 |
| Hold for More Validation | 10 |
| Reject | 24 |
| Promotion Eligible | 0 |

The Validated count dropped from 75 to 40 because incomplete fragments are no longer allowed to upgrade solely through projected centrality. This is an expected quality improvement.

Post-refinement blockers among near-miss concepts with score >= 0.56:

| Blocker | Count |
|---|---:|
| Score below 0.62 | 122 |
| Incomplete proposition | 77 |
| Redundancy above 0.22 | 52 |
| Prompt specificity above 0.16 | 28 |

Post-refinement blockers among concepts already scoring >= 0.62:

| Blocker | Count |
|---|---:|
| Incomplete proposition | 4 |
| Prompt specificity above 0.16 | 3 |

Prompt-shaped or incomplete near-miss concepts remain concentrated in Qwen-derived records:

| Provider | Near-Miss Artifact/Incomplete Count |
|---|---:|
| qwen | 81 |
| unknown | 3 |
| llama | 2 |

Updated conclusion: the largest remaining bottleneck is still proposition-quality at extraction time, with Qwen currently producing most of the near-miss incomplete/prompt-shaped concepts. The promotion gate is behaving conservatively and should not be loosened based on the current evidence.
