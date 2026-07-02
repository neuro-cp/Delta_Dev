# Runtime V1.3 Simulation Failure Analysis

- simulation decision: `REVISE_SIMULATION_FORMULA`

## Failed Metrics

| Metric | Value |
| --- | ---: |
| moved_into_top10_from_outside_top10 | `0` |
| moved_into_top20_from_outside_top10 | `1` |
| original_expected_outside_top10 | `8` |
| original_expected_outside_top20 | `6` |
| original_mean_expected_rank | `10` |
| original_mean_noise_above_expected | `7.7083` |
| original_median_expected_rank | `3` |
| simulated_expected_outside_top10 | `12` |
| simulated_expected_outside_top20 | `11` |
| simulated_mean_expected_rank | `16.6522` |
| simulated_mean_noise_above_expected | `14.0417` |
| simulated_median_expected_rank | `8` |

## Worsened Expected Concepts

### logistics_proxy_planning / 380b765f-ffa2-4296-a66e-527bacb75a64

- rank: `4` -> `33`
- score: `0.3777` -> `0.0777`
- generic terms: `emergency, resource`
- specific terms: `none`
- mostly generic overlap: `True`
- domain relevant despite generic terms: `True`
- likely reason: expected concept depended mostly on domain-generic terms and was over-penalized

### logistics_proxy_planning / 68ae35cf-2be5-4dfc-bdd0-b179682163ad

- rank: `24` -> `50`
- score: `0.3519` -> `0.0319`
- generic terms: `capacity, emergency, resource`
- specific terms: `none`
- mostly generic overlap: `True`
- domain relevant despite generic terms: `True`
- likely reason: expected concept depended mostly on domain-generic terms and was over-penalized

### resource_allocation_shelters / 380b765f-ffa2-4296-a66e-527bacb75a64

- rank: `11` -> `35`
- score: `0.3615` -> `0.3575`
- generic terms: `emergency, resource`
- specific terms: `resources`
- mostly generic overlap: `True`
- domain relevant despite generic terms: `True`
- likely reason: expected concept combined generic domain anchors with specific terms, but the generic penalty dominated

### risk_uncertainty_planning / 4b01b020-00b1-4d40-9422-aba2288625d4

- rank: `2` -> `26`
- score: `0.3991` -> `0.0991`
- generic terms: `failure, plan`
- specific terms: `none`
- mostly generic overlap: `True`
- domain relevant despite generic terms: `True`
- likely reason: expected concept depended mostly on domain-generic terms and was over-penalized

### risk_uncertainty_planning / 98154cbb-a296-4bc9-87e5-83e1e6fbd245

- rank: `4` -> `27`
- score: `0.3958` -> `0.0958`
- generic terms: `failure, risk`
- specific terms: `none`
- mostly generic overlap: `True`
- domain relevant despite generic terms: `True`
- likely reason: expected concept depended mostly on domain-generic terms and was over-penalized

### resource_allocation_shelters / 68ae35cf-2be5-4dfc-bdd0-b179682163ad

- rank: `18` -> `40`
- score: `0.3557` -> `0.3517`
- generic terms: `emergency, resource`
- specific terms: `resources`
- mostly generic overlap: `True`
- domain relevant despite generic terms: `True`
- likely reason: expected concept combined generic domain anchors with specific terms, but the generic penalty dominated

### multi_step_failure_revision / 076c39f2-9cf5-45c7-ac1b-e379da875926

- rank: `6` -> `25`
- score: `0.3749` -> `0.3709`
- generic terms: `evidence, plan`
- specific terms: `revise`
- mostly generic overlap: `True`
- domain relevant despite generic terms: `True`
- likely reason: expected concept combined generic domain anchors with specific terms, but the generic penalty dominated

### contradictory_evidence / a1e249bd-67dc-4056-9120-89380cbe5928

- rank: `3` -> `8`
- score: `0.384` -> `0.426`
- generic terms: `evidence`
- specific terms: `eyewitness, reports`
- mostly generic overlap: `False`
- domain relevant despite generic terms: `True`
- likely reason: expected concept combined generic domain anchors with specific terms, but the generic penalty dominated

### multi_step_failure_revision / e6f9a5a0-a724-48c4-ba2b-5d279555a25e

- rank: `40` -> `43`
- score: `0.3465` -> `0.0665`
- generic terms: `failure`
- specific terms: `none`
- mostly generic overlap: `True`
- domain relevant despite generic terms: `True`
- likely reason: expected concept depended mostly on domain-generic terms and was over-penalized

### causal_industrial_failure / ce828fd3-8630-418e-857b-65904d4fb2ed

- rank: `1` -> `2`
- score: `0.3965` -> `0.5345`
- generic terms: `none`
- specific terms: `causes, industrial, maintenance`
- mostly generic overlap: `False`
- domain relevant despite generic terms: `True`
- likely reason: expected concept was outranked by other concepts after unrelated score shifts

### resource_allocation_shelters / df85054d-ffcd-4c50-8118-ecb512271eaf

- rank: `1` -> `2`
- score: `0.4151` -> `0.5331`
- generic terms: `emergency, resource`
- specific terms: `demand, resources, should`
- mostly generic overlap: `False`
- domain relevant despite generic terms: `True`
- likely reason: expected concept combined generic domain anchors with specific terms, but the generic penalty dominated


## Recurring Noise That Gained Or Survived

| Concept | Before | After | Reason |
| --- | ---: | ---: | --- |
| `5252e50d-b97e-4d57-a79a-b9d64ddbbec7` | `7` | `11` | survived through accidental or broad non-generic overlap: should, demand |
| `5ac48263-cbff-4380-bf63-fc9500bcad8d` | `7` | `11` | survived through accidental or broad non-generic overlap: should |
| `0586e881-099d-4866-a1cf-4ed571139c70` | `7` | `11` | survived through accidental or broad non-generic overlap: should |
| `e0038487-2363-4ba8-8e2e-a1b465c44ee0` | `7` | `11` | survived through accidental or broad non-generic overlap: should |
| `cb4f7649-cbdd-4cb3-905d-6f5f69832e9c` | `6` | `11` | survived through accidental or broad non-generic overlap: should |
| `65e4ca55-7169-4ee4-b388-a6927043a92d` | `5` | `11` | survived through accidental or broad non-generic overlap: should |
| `17a8d30a-9f2d-4d15-8100-d4bf18ca2e71` | `5` | `11` | survived through accidental or broad non-generic overlap: should |
| `89b85467-0655-47d3-9a0c-89da364cd487` | `5` | `11` | survived through accidental or broad non-generic overlap: should |
| `b85b0a01-9c3f-4c42-a26a-01741c84682c` | `5` | `11` | survived through accidental or broad non-generic overlap: should |
| `0e3fdeda-0d38-40ad-993c-480703e55f9e` | `0` | `11` | survived through accidental or broad non-generic overlap: should |
| `06b4d255-58d5-49f5-adec-43426ce0d09b` | `6` | `0` | survived through accidental or broad non-generic overlap: should |

## Improved Vs Worsened Cases

| Case | Diagnosis | Improved | Worsened | Interpretation |
| --- | --- | ---: | ---: | --- |
| causal_industrial_failure | `activation_ranking_primary` | `2` | `1` | formula helped some concepts, but verify gains are not isolated or label-dependent |
| logistics_proxy_planning | `mixed_activation_attention` | `0` | `2` | formula harmed this case; do not use this scoring direction for it |
| multi_step_failure_revision | `mixed_activation_attention` | `0` | `2` | formula harmed this case; do not use this scoring direction for it |
| policy_audit_conflict | `activation_ranking_primary` | `2` | `0` | formula helped some concepts, but verify gains are not isolated or label-dependent |
| resource_allocation_shelters | `activation_ranking_primary` | `0` | `3` | formula harmed this case; do not use this scoring direction for it |
| risk_uncertainty_planning | `attention_primary` | `0` | `2` | formula harmed this case; do not use this scoring direction for it |

## Sparse Behavior

### sparse_violin_tuning

- top score: `0.3501` -> `0.1701`
- sparse behavior ok: `True`
- explanation: the top candidate had only weak stopword/generic overlap and was sufficiently penalized below the abstention threshold
- separate sparse gate recommended: `True`

### unsupported_recipe

- top score: `0.3749` -> `0.1949`
- sparse behavior ok: `False`
- explanation: the top candidate remained above the abstention threshold despite weak overlap; sparse behavior needs a separate abstention gate instead of being folded into normal activation scoring
- separate sparse gate recommended: `True`


## Next Formula Assessment

- `A_revised_generic_token_dampening`: `reject_for_now`
- `B_domain_aware_generic_token_dampening`: `possible_but_not_first`
- `C_query_specific_rarity_weighting`: `possible_with_care`
- `D_duplicate_or_noisy_concept_suppression`: `recommended_next_activation_simulation`
- `E_separate_sparse_abstention_gate`: `recommended_separate_simulation`
- `F_attention_rescue_instead_of_activation_scoring`: `recommended_for_attention_primary_cases`

Rationale:
- 11 expected concepts worsened under blunt generic dampening.
- 10 recurring noisy concepts became more dominant after simulation.
- 2 sparse cases behave structurally differently and should not be folded into normal activation scoring.
- attention-primary cases remain distinct: logistics_proxy_planning, multi_step_failure_revision, risk_uncertainty_planning

## Root cause of failed formula

The formula treated generic task-domain terms as globally weak signals. In the Phase A corpus, words such as resource, risk, plan, failure, and evidence are often the actual domain anchors for valid concepts, so blunt dampening punished expected concepts while allowing other recurring noisy concepts to dominate.

## Recommended next experiment

Do not revise live activation yet. Run a separate simulation for recurring-noise suppression and a separate sparse-abstention simulation. Keep attention rescue as a distinct experiment for attention-primary cases.

## Experiments explicitly rejected

- stronger global generic-token dampening
- live activation scoring changes based on the failed formula
- loosening attention thresholds to compensate for activation noise
- learning/governance/promotion changes

## Metrics to monitor

- expected_outside_top10
- expected_outside_top20
- mean_expected_rank
- mean_noise_above_expected
- expected top-10 concepts pushed out
- sparse top activation score
- noise_used_in_reasoning
- grounding_score
- hallucinations

## Whether to keep, revise, or delete tools/runtime_v13_scoring_simulation.py

Keep it as a failed prototype artifact and baseline simulation harness. Revise by adding alternative named formulas rather than overwriting this result.
