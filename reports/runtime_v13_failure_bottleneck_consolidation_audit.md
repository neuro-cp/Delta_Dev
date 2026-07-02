# Runtime V1.3 Failure Bottleneck Consolidation Audit

Generated: `2026-07-02T13:57:46`

Diagnostic only. No runtime behavior, learning, governance, storage, provider, activation, attention, candidate-store, or canonical systems were modified.

## Summary

- Failed cases audited: `8`
- Case bottleneck distribution: `{'attention_pruned_expected': 2, 'benchmark_expected_concept_outside_live_window': 5, 'activation_rank_unavailable': 1}`
- Concept bottleneck distribution: `{'reasoning_gate_misclassified': 5, 'attention_pruned_expected': 9, 'evaluator_priority_artifact': 2, 'benchmark_expected_concept_outside_live_window': 6, 'activation_rank_unavailable': 2}`
- Final recommendation: `RETURN_TO_ACTIVATION_ATTENTION_DIAGNOSTICS`

## Case Table

| Case | Decision | Primary Bottleneck | Intervention Layer | Downstream Fix Possible | Noise Used | Planning Coverage |
| --- | --- | --- | --- | ---: | ---: | ---: |
| planning_failed_assumption | `Under-Attending` | `attention_pruned_expected` | attention selection diagnostics | `False` | `0` | `0.6667` |
| causal_industrial_failure | `Reasoning Drift` | `benchmark_expected_concept_outside_live_window` | activation/ranking diagnostics | `False` | `4` | `0.6667` |
| contradictory_evidence | `Reasoning Drift` | `attention_pruned_expected` | attention selection diagnostics | `False` | `1` | `0.0` |
| resource_allocation_shelters | `Reasoning Drift` | `activation_rank_unavailable` | activation/ranking diagnostics | `False` | `1` | `0.0` |
| risk_uncertainty_planning | `Reasoning Drift` | `benchmark_expected_concept_outside_live_window` | activation/ranking diagnostics | `False` | `1` | `0.0` |
| policy_audit_conflict | `Planning Drift` | `benchmark_expected_concept_outside_live_window` | activation/ranking diagnostics | `False` | `0` | `0.3333` |
| multi_step_failure_revision | `Under-Attending` | `benchmark_expected_concept_outside_live_window` | activation/ranking diagnostics | `False` | `0` | `0.3333` |
| logistics_proxy_planning | `Under-Attending` | `benchmark_expected_concept_outside_live_window` | activation/ranking diagnostics | `False` | `0` | `0.3333` |

## Expected Concept Traces

### planning_failed_assumption

| Concept ID | Rank | Attention | Working Memory | Reasoning | Planning | Bottleneck | Text |
| --- | ---: | --- | ---: | ---: | ---: | --- | --- |
| aa6c1ba8-9c57-474c-afa5-7383a4733cae | `2` | `True` | `True` | `True` | `True` | `reasoning_gate_misclassified` | When the emergency response plan is disrupted due to a failed permit assumption, the first step is to review the insp... |
| 76120648-7522-4025-8176-5e5fb199c687 | `1` | `True` | `True` | `True` | `True` | `reasoning_gate_misclassified` | When the emergency response plan is disrupted due to a failed permit assumption, the team should use resource telemet... |
| d9ba0c9f-f458-4512-a0e3-40892ef333b6 | `3` | `False` | `False` | `False` | `False` | `attention_pruned_expected` | When a permit assumption fails, the emergency response plan should be revised to include alternative routes or method... |

### causal_industrial_failure

| Concept ID | Rank | Attention | Working Memory | Reasoning | Planning | Bottleneck | Text |
| --- | ---: | --- | ---: | ---: | ---: | --- | --- |
| e3bd802d-b767-4d7d-9dd5-72fb30bd08ce | `2` | `True` | `True` | `True` | `True` | `evaluator_priority_artifact` | In industrial maintenance, when two causes interact, a causal chain can be established by examining the failure timel... |
| ce828fd3-8630-418e-857b-65904d4fb2ed | `1` | `True` | `True` | `True` | `True` | `evaluator_priority_artifact` | In industrial maintenance, when two causes interact, a failure timeline can help identify the root cause by rejecting... |
| 45d9686a-fded-4818-ae8e-47007cd33529 | `37` | `False` | `False` | `False` | `False` | `benchmark_expected_concept_outside_live_window` | In this cycle, the prediction is that if the maintenance frequency is increased further without addressing the root c... |

### contradictory_evidence

| Concept ID | Rank | Attention | Working Memory | Reasoning | Planning | Bottleneck | Text |
| --- | ---: | --- | ---: | ---: | ---: | --- | --- |
| 8430c4bb-9070-4e98-aaa6-90404f2da021 | `2` | `False` | `False` | `False` | `False` | `attention_pruned_expected` | The contradiction in the eyewitness reports remains unresolved due to insufficient evidence to determine which claim ... |
| 0249542c-c698-4a93-805c-8f83c40f8c34 | `7` | `False` | `False` | `False` | `False` | `attention_pruned_expected` | The contradiction lies in the eyewitness reports where the metadata indicates that the events occurred at different t... |
| a1e249bd-67dc-4056-9120-89380cbe5928 | `3` | `False` | `False` | `False` | `False` | `attention_pruned_expected` | However, it's important to note that the resolution could be challenged if new evidence were to emerge, such as corro... |

### resource_allocation_shelters

| Concept ID | Rank | Attention | Working Memory | Reasoning | Planning | Bottleneck | Text |
| --- | ---: | --- | ---: | ---: | ---: | --- | --- |
| 380b765f-ffa2-4296-a66e-527bacb75a64 | `11` | `False` | `False` | `False` | `False` | `activation_rank_unavailable` | The allocation of resources for emergency shelters, given the constraint of one indivisible resource, requires a care... |
| 68ae35cf-2be5-4dfc-bdd0-b179682163ad | `18` | `False` | `False` | `False` | `False` | `activation_rank_unavailable` | The allocation of resources for emergency shelters, given a 20 percent reduction, requires a strategic approach that ... |
| df85054d-ffcd-4c50-8118-ecb512271eaf | `1` | `False` | `False` | `False` | `False` | `attention_pruned_expected` | In the event of unexpected demand spikes for emergency shelters, resources should be reallocated using equity constra... |

### risk_uncertainty_planning

| Concept ID | Rank | Attention | Working Memory | Reasoning | Planning | Bottleneck | Text |
| --- | ---: | --- | ---: | ---: | ---: | --- | --- |
| 52ca9d0c-f68c-429a-afe8-285bf2ceb996 | `None` | `False` | `False` | `False` | `False` | `benchmark_expected_concept_outside_live_window` | Planning compares possible strategies before action by estimating benefit, risk, uncertainty, and goal satisfaction. |
| 4b01b020-00b1-4d40-9422-aba2288625d4 | `2` | `False` | `False` | `False` | `False` | `attention_pruned_expected` | By analyzing the likely failure points and the evidence required to revise the plan, a robust response can be maintained |
| 98154cbb-a296-4bc9-87e5-83e1e6fbd245 | `4` | `False` | `False` | `False` | `False` | `attention_pruned_expected` | The tradeoff in allocating resources for emergency shelters with a 20 percent reduction is that the quality and quant... |

### policy_audit_conflict

| Concept ID | Rank | Attention | Working Memory | Reasoning | Planning | Bottleneck | Text |
| --- | ---: | --- | ---: | ---: | ---: | --- | --- |
| acaca659-aee5-4cef-9c4c-5a2281c1a9ef | `1` | `True` | `True` | `True` | `True` | `reasoning_gate_misclassified` | Reflecting on uncertainty, it is possible that the policy and the audit findings are both correct in their own contex... |
| 1b324e50-0b5b-43b4-befd-f4e6e25d5e01 | `37` | `False` | `False` | `False` | `False` | `benchmark_expected_concept_outside_live_window` | The testable prediction is that if the policy exception is not extended or renewed before it expires, the older opera... |
| 3cc55e56-cb07-4085-a786-afd705a58770 | `22` | `False` | `False` | `False` | `False` | `benchmark_expected_concept_outside_live_window` | The evidence that determines which rule applies is the policy exception's expiration date |

### multi_step_failure_revision

| Concept ID | Rank | Attention | Working Memory | Reasoning | Planning | Bottleneck | Text |
| --- | ---: | --- | ---: | ---: | ---: | --- | --- |
| 4b01b020-00b1-4d40-9422-aba2288625d4 | `1` | `True` | `True` | `True` | `True` | `reasoning_gate_misclassified` | By analyzing the likely failure points and the evidence required to revise the plan, a robust response can be maintained |
| 076c39f2-9cf5-45c7-ac1b-e379da875926 | `6` | `False` | `False` | `False` | `False` | `attention_pruned_expected` | Evidence needed to revise the plan could be a direct communication from Agent B stating that they will not share the ... |
| e6f9a5a0-a724-48c4-ba2b-5d279555a25e | `40` | `False` | `False` | `False` | `False` | `benchmark_expected_concept_outside_live_window` | A prediction that would validate or falsify the system assumption is that after implementing failure drills, the powe... |

### logistics_proxy_planning

| Concept ID | Rank | Attention | Working Memory | Reasoning | Planning | Bottleneck | Text |
| --- | ---: | --- | ---: | ---: | ---: | --- | --- |
| 68ae35cf-2be5-4dfc-bdd0-b179682163ad | `24` | `False` | `False` | `False` | `False` | `benchmark_expected_concept_outside_live_window` | The allocation of resources for emergency shelters, given a 20 percent reduction, requires a strategic approach that ... |
| 76120648-7522-4025-8176-5e5fb199c687 | `1` | `True` | `True` | `True` | `True` | `reasoning_gate_misclassified` | When the emergency response plan is disrupted due to a failed permit assumption, the team should use resource telemet... |
| 380b765f-ffa2-4296-a66e-527bacb75a64 | `4` | `False` | `False` | `False` | `False` | `attention_pruned_expected` | The allocation of resources for emergency shelters, given the constraint of one indivisible resource, requires a care... |

## Interpretation

Most failed cases are limited before downstream role/planning gates can act: expected concepts are outside the effective activation window, outside the benchmark live window, or pruned before reasoning/planning. Downstream Planning Support variants are therefore compensating for upstream candidate availability.

RETURN_TO_ACTIVATION_ATTENTION_DIAGNOSTICS
