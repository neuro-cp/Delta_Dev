# Runtime V1.3 Scoring Simulation

This is a simulation-only report. It does not modify Runtime V1.2 activation, attention, learning, or stores.

Final decision: `REVISE_SIMULATION_FORMULA`

## Baseline Summary

| Metric | Before | After |
| --- | ---: | ---: |
| mean expected rank | `10` | `16.6522` |
| median expected rank | `3` | `8` |
| expected outside top 10 | `8` | `12` |
| expected outside top 20 | `6` | `11` |
| mean noise above expected | `7.7083` | `14.0417` |

## Simulation Formula

original_score - generic_penalty - no_specific_overlap_penalty + specificity_bonus + rare_term_bonus + concept_definition_bonus

Generic tokens dampened:
capacity, change, emergency, evidence, failure, plan, planning, resource, response, risk, uncertainty

Stopwords ignored for specificity:
and, are, best, for, from, how, the, this, what, when, where, why, with

## Aggregate Rank Movement

- expected concepts moved into top 10 from outside top 10: `0`
- expected concepts moved into top 20 from outside top 10: `1`

## Case-Level Rank Movement

| Case | Expected Improved | Expected Worsened | Sparse Top Before | Sparse Top After |
| --- | ---: | ---: | ---: | ---: |
| planning_failed_assumption | `0` | `0` | `None` | `None` |
| causal_industrial_failure | `2` | `1` | `None` | `None` |
| contradictory_evidence | `1` | `1` | `None` | `None` |
| resource_allocation_shelters | `0` | `3` | `None` | `None` |
| risk_uncertainty_planning | `0` | `2` | `None` | `None` |
| policy_audit_conflict | `2` | `0` | `None` | `None` |
| multi_step_failure_revision | `0` | `2` | `None` | `None` |
| logistics_proxy_planning | `0` | `2` | `None` | `None` |
| sparse_violin_tuning | `0` | `0` | `0.3501` | `0.1701` |
| unsupported_recipe | `0` | `0` | `0.3749` | `0.1949` |

## Expected Concepts Improved

- `causal_industrial_failure` `e3bd802d-b767-4d7d-9dd5-72fb30bd08ce` rank `2` -> `1`
- `causal_industrial_failure` `45d9686a-fded-4818-ae8e-47007cd33529` rank `37` -> `35`
- `contradictory_evidence` `0249542c-c698-4a93-805c-8f83c40f8c34` rank `7` -> `5`
- `policy_audit_conflict` `1b324e50-0b5b-43b4-befd-f4e6e25d5e01` rank `37` -> `21`
- `policy_audit_conflict` `3cc55e56-cb07-4085-a786-afd705a58770` rank `22` -> `19`

## Expected Concepts Worsened

- `causal_industrial_failure` `ce828fd3-8630-418e-857b-65904d4fb2ed` rank `1` -> `2`
- `contradictory_evidence` `a1e249bd-67dc-4056-9120-89380cbe5928` rank `3` -> `8`
- `resource_allocation_shelters` `380b765f-ffa2-4296-a66e-527bacb75a64` rank `11` -> `35`
- `resource_allocation_shelters` `68ae35cf-2be5-4dfc-bdd0-b179682163ad` rank `18` -> `40`
- `resource_allocation_shelters` `df85054d-ffcd-4c50-8118-ecb512271eaf` rank `1` -> `2`
- `risk_uncertainty_planning` `4b01b020-00b1-4d40-9422-aba2288625d4` rank `2` -> `26`
- `risk_uncertainty_planning` `98154cbb-a296-4bc9-87e5-83e1e6fbd245` rank `4` -> `27`
- `multi_step_failure_revision` `076c39f2-9cf5-45c7-ac1b-e379da875926` rank `6` -> `25`
- `multi_step_failure_revision` `e6f9a5a0-a724-48c4-ba2b-5d279555a25e` rank `40` -> `43`
- `logistics_proxy_planning` `68ae35cf-2be5-4dfc-bdd0-b179682163ad` rank `24` -> `50`
- `logistics_proxy_planning` `380b765f-ffa2-4296-a66e-527bacb75a64` rank `4` -> `33`

## Noisy Concepts Suppressed

| Concept ID | Before Count | After Count |
| --- | ---: | ---: |
| `0586e881-099d-4866-a1cf-4ed571139c70` | `7` | `11` |
| `06b4d255-58d5-49f5-adec-43426ce0d09b` | `6` | `0` |
| `0e3fdeda-0d38-40ad-993c-480703e55f9e` | `0` | `11` |
| `17a8d30a-9f2d-4d15-8100-d4bf18ca2e71` | `5` | `11` |
| `5252e50d-b97e-4d57-a79a-b9d64ddbbec7` | `7` | `11` |
| `5ac48263-cbff-4380-bf63-fc9500bcad8d` | `7` | `11` |
| `65e4ca55-7169-4ee4-b388-a6927043a92d` | `5` | `11` |
| `89b85467-0655-47d3-9a0c-89da364cd487` | `5` | `11` |
| `b85b0a01-9c3f-4c42-a26a-01741c84682c` | `5` | `11` |
| `cb4f7649-cbdd-4cb3-905d-6f5f69832e9c` | `6` | `11` |
| `e0038487-2363-4ba8-8e2e-a1b465c44ee0` | `7` | `11` |

## Sparse/Unsupported Behavior Check

- `sparse_violin_tuning` top score `0.3501` -> `0.1701`, ok=`True`
- `unsupported_recipe` top score `0.3749` -> `0.1949`, ok=`False`

## Acceptance Criteria Result

- `four_of_eight_outside_top10_move_into_top10_or_top20`: `False`
- `generic_attractor_dominance_decreases`: `False`
- `no_sparse_case_becomes_grounded_false_positive`: `False`
- `expected_outside_top10_decreases`: `False`
- `expected_outside_top20_decreases`: `False`
- `mean_expected_rank_decreases`: `False`
- `mean_noise_above_expected_decreases`: `False`

## Rejection Criteria Result

- `gains_limited_to_one_case`: `False`
- `expected_top10_concepts_pushed_out`: `True`
- `sparse_questions_more_likely_to_activate`: `False`
- `uses_expected_labels_for_scoring`: `False`

## Recommendation For Or Against Live Runtime V1.3 Implementation

Do not implement live runtime changes yet. Revise or compare simulation formulas because acceptance criteria were not fully satisfied or rejection criteria fired.

`REVISE_SIMULATION_FORMULA`