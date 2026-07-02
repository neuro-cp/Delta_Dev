# Runtime V1.3 Remaining Noise Audit

Final recommendation: `PROCEED_QUERY_SPECIFIC_EVIDENCE_MODELING`

This is a read-only diagnostic report. It does not patch runtime behavior, learning, governance, storage, activation recurrence, or canonical knowledge.

## Summary

- remaining noisy reasoning concepts: `7`
- cases with remaining noise: `4`
- successful noise removals: `1`
- unchanged noisy concepts: `7`
- expected/useful concepts at risk: `17`

## Baseline vs Refined Gate Metrics

| Metric | V1.2 Baseline | Refined V1.3 |
| --- | ---: | ---: |
| noise_used_in_reasoning | `8.0` | `7.0` |
| attention_precision | `0.5833` | `0.6333` |
| attention_recall | `0.4333` | `0.4333` |
| retrieval_recall | `0.5333` | `0.5333` |
| retrieval_precision | `0.16` | `0.16` |
| grounding_score | `1.0` | `1.0` |
| hallucinations | `0.0` | `0.0` |
| confidence_calibration | `1.0` | `1.0` |
| planning_score | `1.0` | `1.0` |
| mean_expected_rank | `10` | `10` |
| mean_noise_above_expected | `9.7083` | `9.7083` |

## Per-Case Noise Taxonomy

| Case | Baseline Noise | Refined Noise | Removed | Unchanged | Dominant Causes |
| --- | ---: | ---: | ---: | ---: | --- |
| planning_failed_assumption | `0` | `0` | `0` | `0` | none |
| causal_industrial_failure | `4` | `4` | `0` | `4` | insufficient_query_specific_evidence_modeling: 4, attention_misclassification: 4, reasoning_gate_override_too_permissive: 4, role_ambiguity_between_useful_neighbor_and_noise: 4 |
| contradictory_evidence | `1` | `1` | `0` | `1` | insufficient_query_specific_evidence_modeling: 1, attention_misclassification: 1, reasoning_gate_override_too_permissive: 1, role_ambiguity_between_useful_neighbor_and_noise: 1 |
| resource_allocation_shelters | `1` | `1` | `0` | `1` | insufficient_query_specific_evidence_modeling: 1, attention_misclassification: 1, overly_broad_concept: 1, role_ambiguity_between_useful_neighbor_and_noise: 1, evaluator_or_benchmark_label_issue: 1 |
| risk_uncertainty_planning | `1` | `1` | `0` | `1` | insufficient_query_specific_evidence_modeling: 1, attention_misclassification: 1, overly_broad_concept: 1, missing_concept_role_metadata: 1 |
| policy_audit_conflict | `0` | `0` | `0` | `0` | none |
| multi_step_failure_revision | `1` | `0` | `1` | `0` | none |
| logistics_proxy_planning | `0` | `0` | `0` | `0` | none |
| sparse_violin_tuning | `0` | `0` | `0` | `0` | none |
| unsupported_recipe | `0` | `0` | `0` | `0` | none |

## Remaining Noisy Reasoning Concepts

### causal_industrial_failure / `0fb23c0b-b877-4cf2-a66d-94d927b77542`

- concept: The uncertainty in this scenario lies in the potential confounding variables and the complexity of real world industrial settings where multiple factors can interact
- activation: rank `7`, score `0.352`
- attention: `Core` score `0.4973`
- usage: reasoned=`True`, planned=`True`, responded=`True`
- overlaps: specific `['industrial', 'maintenance']`, domain anchors `['industrial', 'maintenance']`, generic `[]`
- support: evidence_support `1.0`, confidence `0.85`, promotion_score `0.5878`, projected_centrality `0.3433`
- inferred pass reason: `high_corpus_support_plus_context_overlap`
- taxonomy: insufficient_query_specific_evidence_modeling, attention_misclassification, reasoning_gate_override_too_permissive, role_ambiguity_between_useful_neighbor_and_noise
- nearest expected: `e3bd802d-b767-4d7d-9dd5-72fb30bd08ce` with `3` shared terms

### causal_industrial_failure / `183718d2-9612-4057-94b7-4ad8fd896278`

- concept: For instance, if increased maintenance frequency is correlated with higher equipment failure rates, it might be tempting to conclude that frequent maintenance causes failures
- activation: rank `3`, score `0.3571`
- attention: `Supporting` score `0.3941`
- usage: reasoned=`True`, planned=`False`, responded=`False`
- overlaps: specific `['causes', 'maintenance']`, domain anchors `['maintenance']`, generic `[]`
- support: evidence_support `1.0`, confidence `0.85`, promotion_score `0.5945`, projected_centrality `0.2883`
- inferred pass reason: `corpus_support_override`
- taxonomy: insufficient_query_specific_evidence_modeling, attention_misclassification, reasoning_gate_override_too_permissive, role_ambiguity_between_useful_neighbor_and_noise
- nearest expected: `45d9686a-fded-4818-ae8e-47007cd33529` with `5` shared terms

### causal_industrial_failure / `9d5b7363-5857-4091-8449-9374d6b4b68f`

- concept: The current understanding is that causal relationships in industrial maintenance are complex and can be influenced by various factors leading to uncertainty in predicting
- activation: rank `6`, score `0.354`
- attention: `Core` score `0.4951`
- usage: reasoned=`True`, planned=`True`, responded=`True`
- overlaps: specific `['industrial', 'maintenance']`, domain anchors `['industrial', 'maintenance']`, generic `[]`
- support: evidence_support `1.0`, confidence `0.8575`, promotion_score `0.6022`, projected_centrality `0.2883`
- inferred pass reason: `high_corpus_support_plus_context_overlap`
- taxonomy: insufficient_query_specific_evidence_modeling, attention_misclassification, reasoning_gate_override_too_permissive, role_ambiguity_between_useful_neighbor_and_noise
- nearest expected: `e3bd802d-b767-4d7d-9dd5-72fb30bd08ce` with `4` shared terms

### causal_industrial_failure / `c5cc234b-b4ae-4f0c-98f7-c7f04e320abf`

- concept: For instance if a maintenance team observes that a machine s downtime is correlated with a specific type of weather they might mistakenly conclude
- activation: rank `4`, score `0.3568`
- attention: `Supporting` score `0.3974`
- usage: reasoned=`True`, planned=`True`, responded=`True`
- overlaps: specific `['causes', 'maintenance']`, domain anchors `['maintenance']`, generic `[]`
- support: evidence_support `1.0`, confidence `0.85`, promotion_score `0.6`, projected_centrality `0.3433`
- inferred pass reason: `corpus_support_override`
- taxonomy: insufficient_query_specific_evidence_modeling, attention_misclassification, reasoning_gate_override_too_permissive, role_ambiguity_between_useful_neighbor_and_noise
- nearest expected: `45d9686a-fded-4818-ae8e-47007cd33529` with `2` shared terms

### contradictory_evidence / `ef940f21-c49c-41f8-b86e-12a02a0f37f6`

- concept: If the sources are found to be the same, it would suggest that one or both of the reports are inaccurate or contradictory
- activation: rank `5`, score `0.372`
- attention: `Supporting` score `0.6879`
- usage: reasoned=`True`, planned=`True`, responded=`True`
- overlaps: specific `['contradictory']`, domain anchors `['contradictory']`, generic `[]`
- support: evidence_support `1.0`, confidence `0.85`, promotion_score `0.5973`, projected_centrality `0.3433`
- inferred pass reason: `high_corpus_support_plus_context_overlap`
- taxonomy: insufficient_query_specific_evidence_modeling, attention_misclassification, reasoning_gate_override_too_permissive, role_ambiguity_between_useful_neighbor_and_noise
- nearest expected: `0249542c-c698-4a93-805c-8f83c40f8c34` with `2` shared terms

### resource_allocation_shelters / `f567a38f-be7c-4783-972f-d82e8fb2e36f`

- concept: When allocating resources for emergency shelters the tradeoff is between meeting the immediate needs of the priority group and ensuring that the allocation can
- activation: rank `4`, score `0.3933`
- attention: `Supporting` score `0.8123`
- usage: reasoned=`True`, planned=`True`, responded=`True`
- overlaps: specific `[]`, domain anchors `['emergency']`, generic `['change', 'emergency', 'resource']`
- support: evidence_support `1.0`, confidence `0.85`, promotion_score `0.559`, projected_centrality `0.3433`
- inferred pass reason: `high_corpus_support_plus_context_overlap`
- taxonomy: insufficient_query_specific_evidence_modeling, attention_misclassification, overly_broad_concept, role_ambiguity_between_useful_neighbor_and_noise, evaluator_or_benchmark_label_issue
- nearest expected: `68ae35cf-2be5-4dfc-bdd0-b179682163ad` with `6` shared terms

### risk_uncertainty_planning / `d3d08fe0-dbf7-437d-9c46-5c1253dbf9ab`

- concept: Uncertainty The certainty of the revised plan depends on the specific requirements and regulations of the project s location as well as the potential
- activation: rank `7`, score `0.3842`
- attention: `Supporting` score `0.698`
- usage: reasoned=`True`, planned=`True`, responded=`True`
- overlaps: specific `[]`, domain anchors `[]`, generic `['plan', 'uncertainty']`
- support: evidence_support `1.0`, confidence `0.85`, promotion_score `0.5998`, projected_centrality `0.2333`
- inferred pass reason: `supporting_attention_plus_generic_overlap`
- taxonomy: insufficient_query_specific_evidence_modeling, attention_misclassification, overly_broad_concept, missing_concept_role_metadata
- nearest expected: `4b01b020-00b1-4d40-9422-aba2288625d4` with `1` shared terms

## Why Each Noisy Concept Passed The Refined Gate

| Case | Concept | Inferred Pass Reason | Specific Overlap | Domain Anchors | Generic Overlap |
| --- | --- | --- | --- | --- | --- |
| causal_industrial_failure | `0fb23c0b-b877-4cf2-a66d-94d927b77542` | `high_corpus_support_plus_context_overlap` | `['industrial', 'maintenance']` | `['industrial', 'maintenance']` | `[]` |
| causal_industrial_failure | `183718d2-9612-4057-94b7-4ad8fd896278` | `corpus_support_override` | `['causes', 'maintenance']` | `['maintenance']` | `[]` |
| causal_industrial_failure | `9d5b7363-5857-4091-8449-9374d6b4b68f` | `high_corpus_support_plus_context_overlap` | `['industrial', 'maintenance']` | `['industrial', 'maintenance']` | `[]` |
| causal_industrial_failure | `c5cc234b-b4ae-4f0c-98f7-c7f04e320abf` | `corpus_support_override` | `['causes', 'maintenance']` | `['maintenance']` | `[]` |
| contradictory_evidence | `ef940f21-c49c-41f8-b86e-12a02a0f37f6` | `high_corpus_support_plus_context_overlap` | `['contradictory']` | `['contradictory']` | `[]` |
| resource_allocation_shelters | `f567a38f-be7c-4783-972f-d82e8fb2e36f` | `high_corpus_support_plus_context_overlap` | `[]` | `['emergency']` | `['change', 'emergency', 'resource']` |
| risk_uncertainty_planning | `d3d08fe0-dbf7-437d-9c46-5c1253dbf9ab` | `supporting_attention_plus_generic_overlap` | `[]` | `[]` | `['plan', 'uncertainty']` |

## Comparison To Expected Concepts

| Case | Noisy Concept | Nearest Expected | Shared Terms | Jaccard |
| --- | --- | --- | ---: | ---: |
| causal_industrial_failure | `0fb23c0b-b877-4cf2-a66d-94d927b77542` | `e3bd802d-b767-4d7d-9dd5-72fb30bd08ce` | `3` | `0.1071` |
| causal_industrial_failure | `183718d2-9612-4057-94b7-4ad8fd896278` | `45d9686a-fded-4818-ae8e-47007cd33529` | `5` | `0.1852` |
| causal_industrial_failure | `9d5b7363-5857-4091-8449-9374d6b4b68f` | `e3bd802d-b767-4d7d-9dd5-72fb30bd08ce` | `4` | `0.16` |
| causal_industrial_failure | `c5cc234b-b4ae-4f0c-98f7-c7f04e320abf` | `45d9686a-fded-4818-ae8e-47007cd33529` | `2` | `0.0667` |
| contradictory_evidence | `ef940f21-c49c-41f8-b86e-12a02a0f37f6` | `0249542c-c698-4a93-805c-8f83c40f8c34` | `2` | `0.0833` |
| resource_allocation_shelters | `f567a38f-be7c-4783-972f-d82e8fb2e36f` | `68ae35cf-2be5-4dfc-bdd0-b179682163ad` | `6` | `0.24` |
| risk_uncertainty_planning | `d3d08fe0-dbf7-437d-9c46-5c1253dbf9ab` | `4b01b020-00b1-4d40-9422-aba2288625d4` | `1` | `0.04` |
## Successful Noise Removals

- `multi_step_failure_revision` removed `fec7285c-8ebf-45ba-8197-911a515e4e0b`: To predict cascade risk, failure drills can be used to identify dependencies and tradeoffs within the system (baseline attention `Core` -> refined reasoned `False`)

## Noise Remaining Unchanged

- `causal_industrial_failure` kept noisy `0fb23c0b-b877-4cf2-a66d-94d927b77542` at rank `7` with attention `Core` score `0.4973`: The uncertainty in this scenario lies in the potential confounding variables and the complexity of real world industrial settings where multiple factors can interact
- `causal_industrial_failure` kept noisy `183718d2-9612-4057-94b7-4ad8fd896278` at rank `3` with attention `Supporting` score `0.3941`: For instance, if increased maintenance frequency is correlated with higher equipment failure rates, it might be tempting to conclude that frequent maintenance causes failures
- `causal_industrial_failure` kept noisy `9d5b7363-5857-4091-8449-9374d6b4b68f` at rank `6` with attention `Core` score `0.4951`: The current understanding is that causal relationships in industrial maintenance are complex and can be influenced by various factors leading to uncertainty in predicting
- `causal_industrial_failure` kept noisy `c5cc234b-b4ae-4f0c-98f7-c7f04e320abf` at rank `4` with attention `Supporting` score `0.3974`: For instance if a maintenance team observes that a machine s downtime is correlated with a specific type of weather they might mistakenly conclude
- `contradictory_evidence` kept noisy `ef940f21-c49c-41f8-b86e-12a02a0f37f6` at rank `5` with attention `Supporting` score `0.6879`: If the sources are found to be the same, it would suggest that one or both of the reports are inaccurate or contradictory
- `resource_allocation_shelters` kept noisy `f567a38f-be7c-4783-972f-d82e8fb2e36f` at rank `4` with attention `Supporting` score `0.8123`: When allocating resources for emergency shelters the tradeoff is between meeting the immediate needs of the priority group and ensuring that the allocation can
- `risk_uncertainty_planning` kept noisy `d3d08fe0-dbf7-437d-9c46-5c1253dbf9ab` at rank `7` with attention `Supporting` score `0.698`: Uncertainty The certainty of the revised plan depends on the specific requirements and regulations of the project s location as well as the potential

## Expected Or Useful Concepts At Risk

- `planning_failed_assumption` expected `d9ba0c9f-f458-4512-a0e3-40892ef333b6` was rank `3`, attended=`False`, reasoned=`False`: When a permit assumption fails, the emergency response plan should be revised to include alternative routes or methods for the lowest-risk work
- `causal_industrial_failure` expected `45d9686a-fded-4818-ae8e-47007cd33529` was rank `37`, attended=`False`, reasoned=`False`: In this cycle the prediction is that if the maintenance frequency is increased further without addressing the root cause e g equipment age or
- `contradictory_evidence` expected `8430c4bb-9070-4e98-aaa6-90404f2da021` was rank `2`, attended=`False`, reasoned=`False`: The contradiction in the eyewitness reports remains unresolved due to insufficient evidence to determine which claim is incorrect
- `contradictory_evidence` expected `0249542c-c698-4a93-805c-8f83c40f8c34` was rank `7`, attended=`False`, reasoned=`False`: The contradiction lies in the eyewitness reports where the metadata indicates that the events occurred at different times but the content of the reports
- `contradictory_evidence` expected `a1e249bd-67dc-4056-9120-89380cbe5928` was rank `3`, attended=`False`, reasoned=`False`: However it s important to note that the resolution could be challenged if new evidence were to emerge such as corroborating testimony or physical
- `resource_allocation_shelters` expected `380b765f-ffa2-4296-a66e-527bacb75a64` was rank `11`, attended=`False`, reasoned=`False`: The allocation of resources for emergency shelters, given the constraint of one indivisible resource, requires a careful tradeoff between cost and critical service protection
- `resource_allocation_shelters` expected `68ae35cf-2be5-4dfc-bdd0-b179682163ad` was rank `18`, attended=`False`, reasoned=`False`: The allocation of resources for emergency shelters given a 20 percent reduction requires a strategic approach that balances the needs of the most vulnerable
- `resource_allocation_shelters` expected `df85054d-ffcd-4c50-8118-ecb512271eaf` was rank `1`, attended=`False`, reasoned=`False`: In the event of unexpected demand spikes for emergency shelters, resources should be reallocated using equity constraints to ensure fair distribution
- `risk_uncertainty_planning` expected `52ca9d0c-f68c-429a-afe8-285bf2ceb996` was rank `None`, attended=`False`, reasoned=`False`: None
- `risk_uncertainty_planning` expected `4b01b020-00b1-4d40-9422-aba2288625d4` was rank `2`, attended=`False`, reasoned=`False`: By analyzing the likely failure points and the evidence required to revise the plan, a robust response can be maintained
- `risk_uncertainty_planning` expected `98154cbb-a296-4bc9-87e5-83e1e6fbd245` was rank `4`, attended=`False`, reasoned=`False`: The tradeoff in allocating resources for emergency shelters with a 20 percent reduction is that the quality and quantity of services provided may decrease
- `policy_audit_conflict` expected `1b324e50-0b5b-43b4-befd-f4e6e25d5e01` was rank `37`, attended=`False`, reasoned=`False`: The testable prediction is that if the policy exception is not extended or renewed before it expires, the older operating procedure will apply
- `policy_audit_conflict` expected `3cc55e56-cb07-4085-a786-afd705a58770` was rank `22`, attended=`False`, reasoned=`False`: The evidence that determines which rule applies is the policy exception's expiration date
- `multi_step_failure_revision` expected `076c39f2-9cf5-45c7-ac1b-e379da875926` was rank `6`, attended=`False`, reasoned=`False`: Evidence needed to revise the plan could be a direct communication from Agent B stating that they will not share the information, or a history of similar behavior from Agent B
- `multi_step_failure_revision` expected `e6f9a5a0-a724-48c4-ba2b-5d279555a25e` was rank `40`, attended=`False`, reasoned=`False`: A prediction that would validate or falsify the system assumption is that after implementing failure drills the power grid will exhibit improved resilience to
- `logistics_proxy_planning` expected `68ae35cf-2be5-4dfc-bdd0-b179682163ad` was rank `24`, attended=`False`, reasoned=`False`: The allocation of resources for emergency shelters given a 20 percent reduction requires a strategic approach that balances the needs of the most vulnerable
- `logistics_proxy_planning` expected `380b765f-ffa2-4296-a66e-527bacb75a64` was rank `4`, attended=`False`, reasoned=`False`: The allocation of resources for emergency shelters, given the constraint of one indivisible resource, requires a careful tradeoff between cost and critical service protection

## Remaining Failure Modes

- `insufficient_query_specific_evidence_modeling`: `7`
- `attention_misclassification`: `7`
- `role_ambiguity_between_useful_neighbor_and_noise`: `6`
- `reasoning_gate_override_too_permissive`: `5`
- `overly_broad_concept`: `2`
- `evaluator_or_benchmark_label_issue`: `1`
- `missing_concept_role_metadata`: `1`

## Recommended Next Experiment

`PROCEED_QUERY_SPECIFIC_EVIDENCE_MODELING`

The strongest signal is that remaining noise is still generally high-support corpus knowledge with weak or ambiguous query-specific fit. The next safe experiment should model whether a concept supports this exact question before it is allowed to influence reasoning as evidence.

## Explicitly Rejected Experiments

- `stronger_activation_recurrence_by_default`
- `hard_concept_blacklist`
- `global_attention_threshold_loosening`
- `learning_governance_or_promotion_changes`
- `provider_prompt_changes`

`PROCEED_QUERY_SPECIFIC_EVIDENCE_MODELING`
