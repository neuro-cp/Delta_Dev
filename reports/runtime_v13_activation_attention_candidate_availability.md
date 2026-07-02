# Runtime V1.3 Activation/Attention Candidate Availability

Generated: `2026-07-02T14:02:02`

Diagnostic only. No runtime behavior, learning, governance, storage, provider, activation, attention, candidate-store, or canonical systems were modified.

## Summary

- Current accepted default: Model B contextualized corpus support + citation_context reasoning usage gate
- Bucket distribution: `{'inside_top10_selected_by_attention': 7, 'inside_top10_pruned_by_attention': 9, 'outside_top20_inside_top50': 5, 'outside_top10_inside_top20': 2, 'absent_from_diagnostic_top_50': 1}`
- Noise risk estimate: `{'top10_pruned_noise': 51, 'top10_expected': 16, 'rank11_20_expected': 2, 'rank11_20_noise': 78, 'rank21_50_expected': 5, 'rank21_50_noise': 231}`
- Smallest safe next simulation: `bounded attention rescue simulation`

## Case Bottleneck Table

| Case | Decision | Top10 Selected | Top10 Pruned | Rank 11-20 | Rank 21-50 | Absent | Top20 Noise/Expected |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| planning_failed_assumption | `Under-Attending` | `2` | `1` | `0` | `0` | `0` | `10/0` |
| causal_industrial_failure | `Reasoning Drift` | `2` | `0` | `0` | `1` | `0` | `10/0` |
| contradictory_evidence | `Reasoning Drift` | `0` | `3` | `0` | `0` | `0` | `10/0` |
| resource_allocation_shelters | `Reasoning Drift` | `0` | `1` | `2` | `0` | `0` | `8/2` |
| risk_uncertainty_planning | `Reasoning Drift` | `0` | `2` | `0` | `0` | `1` | `10/0` |
| policy_audit_conflict | `Planning Drift` | `1` | `0` | `0` | `2` | `0` | `10/0` |
| multi_step_failure_revision | `Under-Attending` | `1` | `1` | `0` | `1` | `0` | `10/0` |
| logistics_proxy_planning | `Under-Attending` | `1` | `1` | `0` | `1` | `0` | `10/0` |

## Expected Concept Availability

| Case | Concept ID | Bucket | Rank | Attention | Reasoning | Planning | Specific Overlap | Relation Terms | Text |
| --- | --- | --- | ---: | --- | ---: | ---: | --- | --- | --- |
| planning_failed_assumption | aa6c1ba8-9c57-474c-afa5-7383a4733cae | `inside_top10_selected_by_attention` | `2` | `True` | `True` | `True` | `assumption, emergency, failed, permit` | `` | When the emergency response plan is disrupted due to a failed permit assumption, the first step is to revie... |
| planning_failed_assumption | 76120648-7522-4025-8176-5e5fb199c687 | `inside_top10_selected_by_attention` | `1` | `True` | `True` | `True` | `assumption, emergency, failed, permit, should, team` | `` | When the emergency response plan is disrupted due to a failed permit assumption, the team should use resour... |
| planning_failed_assumption | d9ba0c9f-f458-4512-a0e3-40892ef333b6 | `inside_top10_pruned_by_attention` | `3` | `False` | `False` | `False` | `assumption, emergency, permit, should` | `revise` | When a permit assumption fails, the emergency response plan should be revised to include alternative routes... |
| causal_industrial_failure | e3bd802d-b767-4d7d-9dd5-72fb30bd08ce | `inside_top10_selected_by_attention` | `2` | `True` | `True` | `True` | `causes, industrial, maintenance` | `cause` | In industrial maintenance, when two causes interact, a causal chain can be established by examining the fai... |
| causal_industrial_failure | ce828fd3-8630-418e-857b-65904d4fb2ed | `inside_top10_selected_by_attention` | `1` | `True` | `True` | `True` | `causes, industrial, maintenance` | `cause, if, root cause` | In industrial maintenance, when two causes interact, a failure timeline can help identify the root cause by... |
| causal_industrial_failure | 45d9686a-fded-4818-ae8e-47007cd33529 | `outside_top20_inside_top50` | `37` | `False` | `False` | `False` | `maintenance` | `cause, decrease, failure rate, if, increase, prediction, root cause` | In this cycle, the prediction is that if the maintenance frequency is increased further without addressing ... |
| contradictory_evidence | 8430c4bb-9070-4e98-aaa6-90404f2da021 | `inside_top10_pruned_by_attention` | `2` | `False` | `False` | `False` | `eyewitness, reports` | `contradiction, evidence` | The contradiction in the eyewitness reports remains unresolved due to insufficient evidence to determine wh... |
| contradictory_evidence | 0249542c-c698-4a93-805c-8f83c40f8c34 | `inside_top10_pruned_by_attention` | `7` | `False` | `False` | `False` | `eyewitness, reports` | `contradiction, if` | The contradiction lies in the eyewitness reports where the metadata indicates that the events occurred at d... |
| contradictory_evidence | a1e249bd-67dc-4056-9120-89380cbe5928 | `inside_top10_pruned_by_attention` | `3` | `False` | `False` | `False` | `eyewitness, reports` | `evidence, if` | However, it's important to note that the resolution could be challenged if new evidence were to emerge, suc... |
| resource_allocation_shelters | 380b765f-ffa2-4296-a66e-527bacb75a64 | `outside_top10_inside_top20` | `11` | `False` | `False` | `False` | `emergency, resources` | `tradeoff` | The allocation of resources for emergency shelters, given the constraint of one indivisible resource, requi... |
| resource_allocation_shelters | 68ae35cf-2be5-4dfc-bdd0-b179682163ad | `outside_top10_inside_top20` | `18` | `False` | `False` | `False` | `emergency, resources` | `` | The allocation of resources for emergency shelters, given a 20 percent reduction, requires a strategic appr... |
| resource_allocation_shelters | df85054d-ffcd-4c50-8118-ecb512271eaf | `inside_top10_pruned_by_attention` | `1` | `False` | `False` | `False` | `demand, emergency, resources, should` | `reallocate` | In the event of unexpected demand spikes for emergency shelters, resources should be reallocated using equi... |
| risk_uncertainty_planning | 52ca9d0c-f68c-429a-afe8-285bf2ceb996 | `absent_from_diagnostic_top_50` | `None` | `False` | `False` | `False` | `` | `` | Planning compares possible strategies before action by estimating benefit, risk, uncertainty, and goal sati... |
| risk_uncertainty_planning | 4b01b020-00b1-4d40-9422-aba2288625d4 | `inside_top10_pruned_by_attention` | `2` | `False` | `False` | `False` | `and` | `evidence, revise` | By analyzing the likely failure points and the evidence required to revise the plan, a robust response can ... |
| risk_uncertainty_planning | 98154cbb-a296-4bc9-87e5-83e1e6fbd245 | `inside_top10_pruned_by_attention` | `4` | `False` | `False` | `False` | `and, for` | `decrease, tradeoff` | The tradeoff in allocating resources for emergency shelters with a 20 percent reduction is that the quality... |
| policy_audit_conflict | acaca659-aee5-4cef-9c4c-5a2281c1a9ef | `inside_top10_selected_by_attention` | `1` | `True` | `True` | `True` | `and, audit, findings, policy` | `` | Reflecting on uncertainty, it is possible that the policy and the audit findings are both correct in their ... |
| policy_audit_conflict | 1b324e50-0b5b-43b4-befd-f4e6e25d5e01 | `outside_top20_inside_top50` | `37` | `False` | `False` | `False` | `policy` | `exception, if, prediction` | The testable prediction is that if the policy exception is not extended or renewed before it expires, the o... |
| policy_audit_conflict | 3cc55e56-cb07-4085-a786-afd705a58770 | `outside_top20_inside_top50` | `22` | `False` | `False` | `False` | `policy` | `evidence, exception` | The evidence that determines which rule applies is the policy exception's expiration date |
| multi_step_failure_revision | 4b01b020-00b1-4d40-9422-aba2288625d4 | `inside_top10_selected_by_attention` | `1` | `True` | `True` | `True` | `and, points, revise` | `evidence, revise` | By analyzing the likely failure points and the evidence required to revise the plan, a robust response can ... |
| multi_step_failure_revision | 076c39f2-9cf5-45c7-ac1b-e379da875926 | `inside_top10_pruned_by_attention` | `6` | `False` | `False` | `False` | `revise` | `evidence, revise` | Evidence needed to revise the plan could be a direct communication from Agent B stating that they will not ... |
| multi_step_failure_revision | e6f9a5a0-a724-48c4-ba2b-5d279555a25e | `outside_top20_inside_top50` | `40` | `False` | `False` | `False` | `and` | `evidence, if, prediction, validate, would` | A prediction that would validate or falsify the system assumption is that after implementing failure drills... |
| logistics_proxy_planning | 68ae35cf-2be5-4dfc-bdd0-b179682163ad | `outside_top20_inside_top50` | `24` | `False` | `False` | `False` | `capacity, emergency` | `` | The allocation of resources for emergency shelters, given a 20 percent reduction, requires a strategic appr... |
| logistics_proxy_planning | 76120648-7522-4025-8176-5e5fb199c687 | `inside_top10_selected_by_attention` | `1` | `True` | `True` | `True` | `and, emergency, should, team` | `` | When the emergency response plan is disrupted due to a failed permit assumption, the team should use resour... |
| logistics_proxy_planning | 380b765f-ffa2-4296-a66e-527bacb75a64 | `inside_top10_pruned_by_attention` | `4` | `False` | `False` | `False` | `and, emergency` | `tradeoff` | The allocation of resources for emergency shelters, given the constraint of one indivisible resource, requi... |

## Attention-Pruned Expected Concepts

| Case | Concept ID | Rank | Features |
| --- | --- | ---: | --- |
| planning_failed_assumption | d9ba0c9f-f458-4512-a0e3-40892ef333b6 | `3` | specific=`4`, relation=`1`, generic_ratio=`0.3333` |
| contradictory_evidence | 8430c4bb-9070-4e98-aaa6-90404f2da021 | `2` | specific=`2`, relation=`2`, generic_ratio=`0.3333` |
| contradictory_evidence | 0249542c-c698-4a93-805c-8f83c40f8c34 | `7` | specific=`2`, relation=`2`, generic_ratio=`0.0` |
| contradictory_evidence | a1e249bd-67dc-4056-9120-89380cbe5928 | `3` | specific=`2`, relation=`2`, generic_ratio=`0.3333` |
| resource_allocation_shelters | df85054d-ffcd-4c50-8118-ecb512271eaf | `1` | specific=`4`, relation=`1`, generic_ratio=`0.0` |
| risk_uncertainty_planning | 4b01b020-00b1-4d40-9422-aba2288625d4 | `2` | specific=`1`, relation=`2`, generic_ratio=`0.6667` |
| risk_uncertainty_planning | 98154cbb-a296-4bc9-87e5-83e1e6fbd245 | `4` | specific=`2`, relation=`2`, generic_ratio=`0.5` |
| multi_step_failure_revision | 076c39f2-9cf5-45c7-ac1b-e379da875926 | `6` | specific=`1`, relation=`2`, generic_ratio=`0.6667` |
| logistics_proxy_planning | 380b765f-ffa2-4296-a66e-527bacb75a64 | `4` | specific=`2`, relation=`1`, generic_ratio=`0.3333` |

## Top-10/Top-20/Top-50 Miss Table

| Bucket | Count |
| --- | ---: |
| absent_from_diagnostic_top_50 | `1` |
| inside_top10_pruned_by_attention | `9` |
| inside_top10_selected_by_attention | `7` |
| outside_top10_inside_top20 | `2` |
| outside_top20_inside_top50 | `5` |

## Noise Risk Estimate

- Top-10 pruned noise candidates: `51`
- Rank 11-20 expected/noise: `2` / `78`
- Rank 21-50 expected/noise: `5` / `231`

## Rejected Paths

- more Planning Support/QRM variants
- hard concept blacklist
- evaluator-label logic
- benchmark case IDs or concept IDs in live logic
- global threshold loosening
- activation recurrence by default

## Interpretation

The largest immediately actionable availability failure is expected concepts already inside the top-10 activation window but pruned before working memory. This suggests testing a bounded attention rescue before broadening activation.

PROCEED_BOUNDED_ATTENTION_RESCUE_SIMULATION
