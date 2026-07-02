# Phase B Runtime Evaluation Suite

## Aggregate

| Metric | Value |
| --- | ---: |
| case_count | `6.0` |
| pass_rate | `0.3333` |
| retrieval_precision | `0.6028` |
| retrieval_recall | `1.0` |
| grounding_score | `1.0` |
| conflict_score | `1.0` |
| confidence_calibration | `1.0` |
| planning_score | `1.0` |
| hallucinations | `0.0` |
| working_memory_efficiency | `0.6305` |
| planning_utilization_ratio | `0.6305` |
| response_utilization_ratio | `0.6305` |
| overall_utilization_ratio | `0.6305` |
| average_activated_concepts | `4.3333` |
| average_used_concepts | `2.3333` |
| average_ignored_concepts | `2.0` |
| average_noise_concepts | `1.1667` |
| average_useful_neighbors | `1.0` |
| attention_recall | `1.0` |
| attention_precision | `1.0` |
| average_used_noise | `0.0` |
| average_ignored_noise | `1.1667` |
| average_suppressed_core | `0.0` |
| reasoning_contribution_ratio | `0.7778` |
| supporting_ratio | `0.0555` |
| peripheral_ratio | `0.0` |
| noise_used_in_reasoning | `0.0` |
| planning_core_coverage | `1.0` |
| response_core_coverage | `1.0` |
| healthy_cases | `6.0` |
| under_attending_cases | `0.0` |
| reasoning_drift_cases | `0.0` |
| planning_drift_cases | `0.0` |
| response_drift_cases | `0.0` |
| over_attending_cases | `0.0` |

## Categories

| Category | Pass Rate | Retrieval Precision | Retrieval Recall | Attention Precision | Attention Recall | Used Noise | Suppressed Core |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| confidence_calibration | `0.0` | `0.3333` | `1.0` | `1.0` | `1.0` | `0.0` | `0.0` |
| conflict_handling | `0.0` | `0.3333` | `1.0` | `1.0` | `1.0` | `0.0` | `0.0` |
| planning | `0.0` | `0.6` | `1.0` | `1.0` | `1.0` | `0.0` | `0.0` |
| retrieval_accuracy | `1.0` | `0.75` | `1.0` | `1.0` | `1.0` | `0.0` | `0.0` |
| runtime_stability | `0.0` | `0.6` | `1.0` | `1.0` | `1.0` | `0.0` | `0.0` |
| sparse_knowledge | `1.0` | `1.0` | `1.0` | `1.0` | `1.0` | `0.0` | `0.0` |

## Case Scorecards

### gps_drift_retrieval

- category: `retrieval_accuracy`
- passed: `True`
- activated: `gps-satellite-geometry, gps-multipath, snow-plow-positioning, gps-atmospheric-delay`
- retrieval precision: `0.75`
- retrieval recall: `1.0`
- grounding: `1.0`
- conflict score: `1.0`
- confidence calibration: `1.0`
- planning score: `1.0`
- working memory efficiency: `0.75`
- response utilization: `0.75`
- overall utilization: `0.75`
- useful neighbors: `0`
- noise concepts: `1`
- ignored concepts: `1`
- attention recall: `1.0`
- attention precision: `1.0`
- used noise: `0`
- suppressed core: `0`
- reasoning contribution ratio: `1.0`
- supporting ratio: `0.0`
- peripheral ratio: `0.0`
- noise used in reasoning: `0`
- runtime decision: `Healthy`
- hallucinations: `0`
- notes: irrelevant concepts activated: snow-plow-positioning; activation noise detected: 1; ignored activations: 1

### snowstorm_grounded_planning

- category: `planning`
- passed: `False`
- activated: `snow-plow-positioning, shelter-capacity, emergency-route-priority, resource-allocation-triage, risk-likelihood-impact`
- retrieval precision: `0.6`
- retrieval recall: `1.0`
- grounding: `1.0`
- conflict score: `1.0`
- confidence calibration: `1.0`
- planning score: `1.0`
- working memory efficiency: `0.6`
- response utilization: `0.6`
- overall utilization: `0.6`
- useful neighbors: `2`
- noise concepts: `0`
- ignored concepts: `2`
- attention recall: `1.0`
- attention precision: `1.0`
- used noise: `0`
- suppressed core: `0`
- reasoning contribution ratio: `1.0`
- supporting ratio: `0.0`
- peripheral ratio: `0.0`
- noise used in reasoning: `0`
- runtime decision: `Healthy`
- hallucinations: `0`
- notes: irrelevant concepts activated: resource-allocation-triage, risk-likelihood-impact; ignored activations: 2

### salt_tradeoff_conflict

- category: `conflict_handling`
- passed: `False`
- activated: `salt-traction-benefit, salt-environmental-cost, snow-plow-positioning, shelter-capacity, emergency-route-priority, resource-allocation-triage`
- retrieval precision: `0.3333`
- retrieval recall: `1.0`
- grounding: `1.0`
- conflict score: `1.0`
- confidence calibration: `1.0`
- planning score: `1.0`
- working memory efficiency: `0.3333`
- response utilization: `0.3333`
- overall utilization: `0.3333`
- useful neighbors: `0`
- noise concepts: `4`
- ignored concepts: `4`
- attention recall: `1.0`
- attention precision: `1.0`
- used noise: `0`
- suppressed core: `0`
- reasoning contribution ratio: `1.0`
- supporting ratio: `0.0`
- peripheral ratio: `0.0`
- noise used in reasoning: `0`
- runtime decision: `Healthy`
- hallucinations: `0`
- notes: irrelevant concepts activated: emergency-route-priority, resource-allocation-triage, shelter-capacity, snow-plow-positioning; activation noise detected: 4; ignored activations: 4

### resource_allocation_calibration

- category: `confidence_calibration`
- passed: `False`
- activated: `resource-allocation-triage, emergency-route-priority, snow-plow-positioning, risk-likelihood-impact, shelter-capacity, salt-traction-benefit`
- retrieval precision: `0.3333`
- retrieval recall: `1.0`
- grounding: `1.0`
- conflict score: `1.0`
- confidence calibration: `1.0`
- planning score: `1.0`
- working memory efficiency: `0.5`
- response utilization: `0.5`
- overall utilization: `0.5`
- useful neighbors: `2`
- noise concepts: `2`
- ignored concepts: `3`
- attention recall: `1.0`
- attention precision: `1.0`
- used noise: `0`
- suppressed core: `0`
- reasoning contribution ratio: `0.6667`
- supporting ratio: `0.3333`
- peripheral ratio: `0.0`
- noise used in reasoning: `0`
- runtime decision: `Healthy`
- hallucinations: `0`
- notes: irrelevant concepts activated: emergency-route-priority, salt-traction-benefit, shelter-capacity, snow-plow-positioning; activation noise detected: 2; ignored activations: 3

### sparse_violin_question

- category: `sparse_knowledge`
- passed: `True`
- activated: `none`
- retrieval precision: `1.0`
- retrieval recall: `1.0`
- grounding: `1.0`
- conflict score: `1.0`
- confidence calibration: `1.0`
- planning score: `1.0`
- working memory efficiency: `1.0`
- response utilization: `1.0`
- overall utilization: `1.0`
- useful neighbors: `0`
- noise concepts: `0`
- ignored concepts: `0`
- attention recall: `1.0`
- attention precision: `1.0`
- used noise: `0`
- suppressed core: `0`
- reasoning contribution ratio: `0.0`
- supporting ratio: `0.0`
- peripheral ratio: `0.0`
- noise used in reasoning: `0`
- runtime decision: `Healthy`
- hallucinations: `0`

### repeat_snowstorm_stability

- category: `runtime_stability`
- passed: `False`
- activated: `snow-plow-positioning, shelter-capacity, emergency-route-priority, resource-allocation-triage, risk-likelihood-impact`
- retrieval precision: `0.6`
- retrieval recall: `1.0`
- grounding: `1.0`
- conflict score: `1.0`
- confidence calibration: `1.0`
- planning score: `1.0`
- working memory efficiency: `0.6`
- response utilization: `0.6`
- overall utilization: `0.6`
- useful neighbors: `2`
- noise concepts: `0`
- ignored concepts: `2`
- attention recall: `1.0`
- attention precision: `1.0`
- used noise: `0`
- suppressed core: `0`
- reasoning contribution ratio: `1.0`
- supporting ratio: `0.0`
- peripheral ratio: `0.0`
- noise used in reasoning: `0`
- runtime decision: `Healthy`
- hallucinations: `0`
- notes: irrelevant concepts activated: resource-allocation-triage, risk-likelihood-impact; ignored activations: 2
