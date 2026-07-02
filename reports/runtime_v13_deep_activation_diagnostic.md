# Runtime V1.3 Deep Activation Diagnostic

Generated: `2026-07-02T14:21:49`

Diagnostic only. No runtime behavior, learning, governance, storage, provider, candidate-store, canonical, benchmark, or default runtime behavior was modified.

## Summary

- Current accepted default: Model B contextualized corpus support + citation_context reasoning usage gate
- Autonomous reranking stopped: `same_failure_repeated` / `PROCEED_DEEP_ACTIVATION_DIAGNOSTICS`
- Availability prior: `{'final_recommendation': 'PROCEED_BOUNDED_ATTENTION_RESCUE_SIMULATION', 'bucket_distribution': {'absent_from_diagnostic_top_50': 1, 'inside_top10_pruned_by_attention': 9, 'inside_top10_selected_by_attention': 7, 'outside_top10_inside_top20': 2, 'outside_top20_inside_top50': 5}, 'noise_risk_estimate': {'rank11_20_expected': 2, 'rank11_20_noise': 78, 'rank21_50_expected': 5, 'rank21_50_noise': 231, 'top10_expected': 16, 'top10_pruned_noise': 51}}`
- Final recommendation: `PROCEED_RELATION_AWARE_ACTIVATION_SIMULATION`

## Root-Cause Ranking

| Rank | Mechanism | Score |
| ---: | --- | ---: |
| 1 | lexical overlap / same-topic dominance | `69` |
| 2 | centrality/recurrence bias | `60` |
| 3 | generic-anchor dominance | `21` |
| 4 | confidence/promotion over-weighting | `15` |
| 5 | benchmark expected concept outside realistic live window | `6` |
| 6 | query decomposition failure | `4` |
| 7 | relation mismatch / missing relation-aware activation | `2` |

## Case-Level Activation Failure Table

| Case | Decision | Missed Rank Bands | Dominant Noise Taxonomy |
| --- | --- | --- | --- |
| planning_failed_assumption | `Under-Attending` | `{'rank_1_10': 1}` | `[('centrality_competes', 7), ('generic_anchor_heavy', 5), ('same_relation_terms', 3)]` |
| causal_industrial_failure | `Reasoning Drift` | `{'rank_21_50': 1}` | `[('centrality_competes', 7), ('same_query_terms', 5), ('same_relation_terms', 3)]` |
| contradictory_evidence | `Reasoning Drift` | `{'rank_1_10': 3}` | `[('centrality_competes', 8), ('generic_anchor_heavy', 7), ('same_query_terms', 5)]` |
| resource_allocation_shelters | `Reasoning Drift` | `{'rank_1_10': 1, 'rank_11_20': 2}` | `[('same_relation_terms', 7), ('centrality_competes', 7), ('same_query_terms', 6)]` |
| risk_uncertainty_planning | `Reasoning Drift` | `{'rank_1_10': 2, 'absent': 1}` | `[('same_query_terms', 7), ('same_relation_terms', 6), ('centrality_competes', 6)]` |
| policy_audit_conflict | `Planning Drift` | `{'rank_21_50': 2}` | `[('same_query_terms', 10), ('centrality_competes', 9), ('confidence_promotion_competes', 2)]` |
| multi_step_failure_revision | `Under-Attending` | `{'rank_1_10': 1, 'rank_21_50': 1}` | `[('same_query_terms', 9), ('centrality_competes', 7), ('same_relation_terms', 2)]` |
| logistics_proxy_planning | `Under-Attending` | `{'rank_1_10': 1, 'rank_21_50': 1}` | `[('centrality_competes', 9), ('generic_anchor_heavy', 6), ('confidence_promotion_competes', 3)]` |

## Expected-vs-Noise Feature Deltas

| Case | Activation | Specific | Generic Ratio | Relation | Confidence | Promotion | Centrality |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| planning_failed_assumption | `0.1008` | `2.9667` | `0.0723` | `0.3` | `0.003` | `-0.0092` | `-0.0427` |
| causal_industrial_failure | `0.0235` | `0.8333` | `0.0` | `1.7333` | `0.0028` | `-0.0089` | `-0.0018` |
| contradictory_evidence | `0.0155` | `0.5` | `-0.0945` | `0.4333` | `0.003` | `0.0162` | `0.0325` |
| resource_allocation_shelters | `-0.0034` | `-0.2333` | `0.0` | `-0.0667` | `0.0045` | `0.0189` | `0.033` |
| risk_uncertainty_planning | `0.0123` | `-0.3` | `0.15` | `-0.3` | `0.003` | `0.0411` | `0.0385` |
| policy_audit_conflict | `-0.01` | `0.0` | `0.0` | `0.8667` | `0.001` | `0.0075` | `0.0055` |
| multi_step_failure_revision | `0.0286` | `-0.4333` | `0.2639` | `1.0` | `0.0037` | `0.0398` | `0.0123` |
| logistics_proxy_planning | `0.0143` | `0.8667` | `-0.0278` | `0.5667` | `0.0045` | `0.0104` | `-0.0257` |

## Same-Topic Noise Taxonomy

- `centrality_competes`: `60`
- `same_query_terms`: `43`
- `same_relation_terms`: `26`
- `generic_anchor_heavy`: `21`
- `confidence_promotion_competes`: `15`

## Failed Rerank Noise Examples

### planning_failed_assumption
- `d3d08fe0-dbf7-437d-9c46-5c1253dbf9ab` rank `5`: Uncertainty The certainty of the revised plan depends on the specific requirements and regulations of the project s location as well as t...
- `06b4d255-58d5-49f5-adec-43426ce0d09b` rank `6`: Each party's likely belief should be acknowledged, and a prediction about their response should be made
- `df85054d-ffcd-4c50-8118-ecb512271eaf` rank `7`: In the event of unexpected demand spikes for emergency shelters, resources should be reallocated using equity constraints to ensure fair ...
- `0586e881-099d-4866-a1cf-4ed571139c70` rank `8`: These records should provide evidence of whether the purchase was indeed an emergency one and, if so, whether the appropriate steps were ...
- `3a9f7658-b877-4532-b9c8-1a79b360c5d4` rank `10`: Delta should revise its belief to acknowledge that while GPS estimates are generally reliable in downtown areas, they can be unreliable i...

### causal_industrial_failure
- `183718d2-9612-4057-94b7-4ad8fd896278` rank `3`: For instance, if increased maintenance frequency is correlated with higher equipment failure rates, it might be tempting to conclude that...
- `c5cc234b-b4ae-4f0c-98f7-c7f04e320abf` rank `4`: For instance if a maintenance team observes that a machine s downtime is correlated with a specific type of weather they might mistakenly...
- `b1f3eca3-5024-45c1-a91d-68ef0d7d28e5` rank `5`: This cycle can be completed by making a testable prediction: if the maintenance introduces stress, then reducing the frequency of mainten...
- `9d5b7363-5857-4091-8449-9374d6b4b68f` rank `6`: The current understanding is that causal relationships in industrial maintenance are complex and can be influenced by various factors lea...
- `0fb23c0b-b877-4cf2-a66d-94d927b77542` rank `7`: The uncertainty in this scenario lies in the potential confounding variables and the complexity of real world industrial settings where m...

### contradictory_evidence
- `ef940f21-c49c-41f8-b86e-12a02a0f37f6` rank `5`: If the sources are found to be the same, it would suggest that one or both of the reports are inaccurate or contradictory
- `011d4f3b-e7d2-4865-9fe3-b269795e07cb` rank `11`: The prediction that would confirm the resolution is that the sources of the reports are indeed different or that they are the same but
- `0586e881-099d-4866-a1cf-4ed571139c70` rank `13`: These records should provide evidence of whether the purchase was indeed an emergency one and, if so, whether the appropriate steps were ...
- `41cc8fe7-a7a2-4cd9-8e17-4c5336b8ac28` rank `15`: One contradiction in the eyewitness reports is that two trusted sources disagree on the color of a car involved in an accident
- `65e4ca55-7169-4ee4-b388-a6927043a92d` rank `16`: Customer communication should be revised next, as it is closely tied to the revised delivery dates and staffing levels

### resource_allocation_shelters
- `6b704bd9-ecc5-4066-b351-a4eda0ba5c8d` rank `2`: If the generator is allocated to a shelter with higher demand, it may not be available when needed elsewhere, leading to potential failures
- `f567a38f-be7c-4783-972f-d82e8fb2e36f` rank `4`: When allocating resources for emergency shelters the tradeoff is between meeting the immediate needs of the priority group and ensuring t...
- `2ecb3022-1ce7-46e9-b1e5-4da1ffd0ac7d` rank `5`: Tradeoffs in allocating resources for emergency shelters, particularly when one resource is indivisible, involve balancing equity and eff...
- `76120648-7522-4025-8176-5e5fb199c687` rank `6`: When the emergency response plan is disrupted due to a failed permit assumption the team should use resource telemetry data to assess the...
- `d9ba0c9f-f458-4512-a0e3-40892ef333b6` rank `7`: When a permit assumption fails, the emergency response plan should be revised to include alternative routes or methods for the lowest-ris...

### risk_uncertainty_planning
- `d9ba0c9f-f458-4512-a0e3-40892ef333b6` rank `1`: When a permit assumption fails, the emergency response plan should be revised to include alternative routes or methods for the lowest-ris...
- `cb4f7649-cbdd-4cb3-905d-6f5f69832e9c` rank `3`: Staffing should be revised first, as it directly impacts the number of personnel needed for inspections and delivery
- `d3d08fe0-dbf7-437d-9c46-5c1253dbf9ab` rank `7`: Uncertainty The certainty of the revised plan depends on the specific requirements and regulations of the project s location as well as t...
- `7b1fd455-c6f7-4dcf-a109-11fc3c89262f` rank `9`: For instance if a machine part A fails due to wear and tear and this failure leads to part B failing due to increased
- `77b37207-0a4f-4af1-a029-1ead85cc56ce` rank `14`: The uncertainty in demand forecasts means that the allocation strategy must be robust and adaptable

### policy_audit_conflict
- `17a8d30a-9f2d-4d15-8100-d4bf18ca2e71` rank `2`: Each agent's belief and incentives should be identified and understood to predict potential handoff failures
- `65e4ca55-7169-4ee4-b388-a6927043a92d` rank `3`: Customer communication should be revised next, as it is closely tied to the revised delivery dates and staffing levels
- `b85b0a01-9c3f-4c42-a26a-01741c84682c` rank `5`: However, this reallocation should be temporary and should not compromise long-term preparedness
- `cb4f7649-cbdd-4cb3-905d-6f5f69832e9c` rank `7`: Staffing should be revised first, as it directly impacts the number of personnel needed for inspections and delivery
- `5252e50d-b97e-4d57-a79a-b9d64ddbbec7` rank `8`: Service-level data, such as historical usage patterns, demographic information, and current demand, should guide the reallocation

### multi_step_failure_revision
- `76120648-7522-4025-8176-5e5fb199c687` rank `4`: When the emergency response plan is disrupted due to a failed permit assumption the team should use resource telemetry data to assess the...
- `0586e881-099d-4866-a1cf-4ed571139c70` rank `5`: These records should provide evidence of whether the purchase was indeed an emergency one and, if so, whether the appropriate steps were ...
- `3a9f7658-b877-4532-b9c8-1a79b360c5d4` rank `8`: Delta should revise its belief to acknowledge that while GPS estimates are generally reliable in downtown areas, they can be unreliable i...
- `22471376-888c-42fb-ac5d-c06d09f25345` rank `9`: To identify each party's likely belief, predict their response, and determine evidence that would change the strategy, you can follow the...
- `17a8d30a-9f2d-4d15-8100-d4bf18ca2e71` rank `12`: Each agent's belief and incentives should be identified and understood to predict potential handoff failures

### logistics_proxy_planning
- `06b4d255-58d5-49f5-adec-43426ce0d09b` rank `2`: Each party's likely belief should be acknowledged, and a prediction about their response should be made
- `2ecb3022-1ce7-46e9-b1e5-4da1ffd0ac7d` rank `3`: Tradeoffs in allocating resources for emergency shelters, particularly when one resource is indivisible, involve balancing equity and eff...
- `0586e881-099d-4866-a1cf-4ed571139c70` rank `5`: These records should provide evidence of whether the purchase was indeed an emergency one and, if so, whether the appropriate steps were ...
- `d9ba0c9f-f458-4512-a0e3-40892ef333b6` rank `6`: When a permit assumption fails, the emergency response plan should be revised to include alternative routes or methods for the lowest-ris...
- `17a8d30a-9f2d-4d15-8100-d4bf18ca2e71` rank `8`: Each agent's belief and incentives should be identified and understood to predict potential handoff failures

## Rejected Mitigation Paths

- more downstream Planning Support/QRM variants
- bounded attention rescue as a live patch
- broad activation-window expansion
- activation recurrence by default
- concept-ID or benchmark-case-specific live logic
- global threshold loosening

## Recommended Next Experiment

PROCEED_RELATION_AWARE_ACTIVATION_SIMULATION

## Continuation Checkpoint

- Model B default remains active: `True`
- Runtime files modified: `False`
- Next step: `PROCEED_RELATION_AWARE_ACTIVATION_SIMULATION`

PROCEED_RELATION_AWARE_ACTIVATION_SIMULATION
