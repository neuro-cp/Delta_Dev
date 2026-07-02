# Phase 27 Knowledge Maturation Audit

This audit is read-only over the Phase 26 isolated experiment stores. No canonical knowledge was modified.

## Executive Summary

- Promotion-eligible concepts inspected: `12`
- Eligible score average: `0.6462`
- Eligible score range: `{'min': 0.62, 'max': 0.6773}`
- Eligible by provider: `{'qwen': 10, 'mistral': 1, 'llama': 1}`
- Eligible by profile: `{'unknown': 5, 'resource_allocation': 3, 'risk_assessment': 1, 'contradiction': 1, 'negotiation': 1, 'tool_use': 1}`
- Primary unresolved-prediction cause: `source_concept_missing_or_superseded`
- Primary current-concept backlog cause: `redundant_current_concept_backlog`
- Primary redundancy cause: `accepted_overlap_reusable`

## Run Comparison

| Run | Cycles | Semantic Growth | Validated | Eligible | Rejected | Avg Score | Top Unresolved Cause |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| broad_balanced_100 | 100 | 147 | 72 | 2 | 11 | 0.5373 | source_concept_missing_or_superseded |
| broad_balanced_200 | 200 | 314 | 167 | 1 | 37 | 0.522 | source_concept_missing_or_superseded |
| causal_reasoning_100 | 100 | 43 | 29 | 2 | 0 | 0.5846 | source_concept_missing_or_superseded |
| causal_reasoning_200 | 104 | 45 | 27 | 2 | 1 | 0.5776 | source_concept_missing_or_superseded |
| contradiction_100 | 100 | 39 | 27 | 1 | 1 | 0.5585 | source_concept_missing_or_superseded |
| planning_100 | 100 | 81 | 44 | 2 | 6 | 0.5451 | source_concept_missing_or_superseded |
| planning_200 | 200 | 143 | 82 | 2 | 7 | 0.5572 | source_concept_missing_or_superseded |

## Promotion-Eligible Concepts

| Run | Score | Provider | Profile | Origin Tick | Supported Predictions | Open Contradictions | Redundancy | Concept |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| broad_balanced_100 | 0.6679 | qwen | risk_assessment | 59 | 1 | 0 | 0.125 | However, the positive trend in user satisfaction and the recent implementation of a new security protocol may offset som |
| broad_balanced_100 | 0.6621 | mistral | contradiction | 12 | 1 | 0 | 0.1923 | The prediction that would confirm the resolution is if further investigation reveals additional evidence e g surveillanc |
| broad_balanced_200 | 0.6654 | llama | negotiation | 198 | 1 | 0 | 0.1429 | By leveraging deadline records, one can make informed decisions about when to make a move in the negotiation |
| causal_reasoning_100 | 0.622 | qwen | unknown | 28 | 1 | 0 | 0.0741 | This revised belief is based on evidence from repeated observations, which indicate that GPS performance degrades signif |
| causal_reasoning_100 | 0.62 | qwen | unknown | 87 | 1 | 0 | 0.1 | Prediction: If the city experiences a mild winter, the reduced snow budget will be sufficient, and the city will have sa |
| causal_reasoning_200 | 0.6223 | qwen | unknown | 28 | 1 | 0 | 0.0714 | This revised belief is based on evidence from repeated observations, which indicate that GPS performance degrades signif |
| causal_reasoning_200 | 0.62 | qwen | unknown | 104 | 1 | 0 | 0.1 | Prediction: If the city experiences a mild winter, the reduced snow budget will be sufficient, and the city will have sa |
| contradiction_100 | 0.6773 | qwen | unknown | 23 | 1 | 0 | 0.0833 | Prediction If the comparison reveals that the government report s data and methodology are less rigorous than the scient |
| planning_100 | 0.6666 | qwen | resource_allocation | 21 | 1 | 0 | 0.16 | A prediction is that if the reallocation is not done promptly the number of unmet needs will increase resulting in highe |
| planning_100 | 0.6525 | qwen | resource_allocation | 42 | 1 | 0 | 0.1818 | The cost records will guide the reallocation, but there is a risk of underfunding the ongoing needs of the current prior |
| planning_200 | 0.6574 | qwen | resource_allocation | 93 | 1 | 0 | 0.1471 | The tradeoff lies in the allocation of scarce capacity prioritizing immediate relief can lead to overburdened shelters a |
| planning_200 | 0.6211 | qwen | tool_use | 7 | 1 | 0 | 0.08 | Expected evidence includes log entries related to the incident, such as error messages, warnings, or unusual activity |

## Promotion Survivor Profiles

### broad_balanced_100 / ae290d12-d66d-49f7-aa04-f96d6592d722

Concept: However, the positive trend in user satisfaction and the recent implementation of a new security protocol may offset some of this risk

- Origin profile: `risk_assessment`
- Provider: `qwen`
- First learned cycle: `59`
- Validation history: supported `1`, failed `0`, unresolved `0`
- Contradictions: `0`
- Redundancy: `0.125`
- Projected centrality: `0.3433`
- Confidence trajectory: `[0.8, 0.8413]`
- Confidence slope: `0.0413`
- Supporting memories: `2`
- Supporting memory relationship edges: `1`
- Related concepts: `3`
- Prediction accuracy: `1.0`
- Final recommendation: `Promotion Eligible`

### broad_balanced_100 / 6e71b4d3-d2e8-4d69-bb84-6a2c0ac2dd9c

Concept: The prediction that would confirm the resolution is if further investigation reveals additional evidence e g surveillance footage eyewitness interviews or physical evidence that

- Origin profile: `contradiction`
- Provider: `mistral`
- First learned cycle: `12`
- Validation history: supported `1`, failed `0`, unresolved `0`
- Contradictions: `0`
- Redundancy: `0.1923`
- Projected centrality: `0.3433`
- Confidence trajectory: `[0.8, 0.8575]`
- Confidence slope: `0.0575`
- Supporting memories: `2`
- Supporting memory relationship edges: `1`
- Related concepts: `3`
- Prediction accuracy: `1.0`
- Final recommendation: `Promotion Eligible`

### broad_balanced_200 / 57500598-b5e7-4ea0-8f02-882e8ff7f6f8

Concept: By leveraging deadline records, one can make informed decisions about when to make a move in the negotiation

- Origin profile: `negotiation`
- Provider: `llama`
- First learned cycle: `198`
- Validation history: supported `1`, failed `0`, unresolved `0`
- Contradictions: `0`
- Redundancy: `0.1429`
- Projected centrality: `0.3433`
- Confidence trajectory: `[0.8, 0.8413]`
- Confidence slope: `0.0413`
- Supporting memories: `2`
- Supporting memory relationship edges: `1`
- Related concepts: `3`
- Prediction accuracy: `1.0`
- Final recommendation: `Promotion Eligible`

### causal_reasoning_100 / 92c440de-b5d6-4f32-b1a9-0eb55a829adc

Concept: This revised belief is based on evidence from repeated observations, which indicate that GPS performance degrades significantly in such environments

- Origin profile: `unknown`
- Provider: `qwen`
- First learned cycle: `28`
- Validation history: supported `1`, failed `0`, unresolved `0`
- Contradictions: `0`
- Redundancy: `0.0741`
- Projected centrality: `0.3433`
- Confidence trajectory: `[0.8, 0.85]`
- Confidence slope: `0.05`
- Supporting memories: `2`
- Supporting memory relationship edges: `1`
- Related concepts: `3`
- Prediction accuracy: `1.0`
- Final recommendation: `Promotion Eligible`

### causal_reasoning_100 / 8e078e10-d3de-47bd-929f-15c09e141ed2

Concept: Prediction: If the city experiences a mild winter, the reduced snow budget will be sufficient, and the city will have saved costs without compromising safety and accessibility

- Origin profile: `unknown`
- Provider: `qwen`
- First learned cycle: `87`
- Validation history: supported `1`, failed `0`, unresolved `0`
- Contradictions: `0`
- Redundancy: `0.1`
- Projected centrality: `0.3433`
- Confidence trajectory: `[0.8, 0.8575]`
- Confidence slope: `0.0575`
- Supporting memories: `2`
- Supporting memory relationship edges: `1`
- Related concepts: `3`
- Prediction accuracy: `1.0`
- Final recommendation: `Promotion Eligible`

### causal_reasoning_200 / cc8865b3-7355-496a-ade3-778a1b917f1a

Concept: This revised belief is based on evidence from repeated observations, which indicate that GPS performance degrades significantly in such environments

- Origin profile: `unknown`
- Provider: `qwen`
- First learned cycle: `28`
- Validation history: supported `1`, failed `0`, unresolved `0`
- Contradictions: `0`
- Redundancy: `0.0714`
- Projected centrality: `0.3433`
- Confidence trajectory: `[0.8, 0.85]`
- Confidence slope: `0.05`
- Supporting memories: `2`
- Supporting memory relationship edges: `1`
- Related concepts: `3`
- Prediction accuracy: `1.0`
- Final recommendation: `Promotion Eligible`

### causal_reasoning_200 / 2ab102e7-8dcc-4243-8dbf-346f80a7be4d

Concept: Prediction: If the city experiences a mild winter, the reduced snow budget will be sufficient, and the city will have saved costs without compromising safety and accessibility

- Origin profile: `unknown`
- Provider: `qwen`
- First learned cycle: `104`
- Validation history: supported `1`, failed `0`, unresolved `0`
- Contradictions: `0`
- Redundancy: `0.1`
- Projected centrality: `0.3433`
- Confidence trajectory: `[0.8, 0.8575]`
- Confidence slope: `0.0575`
- Supporting memories: `2`
- Supporting memory relationship edges: `1`
- Related concepts: `3`
- Prediction accuracy: `1.0`
- Final recommendation: `Promotion Eligible`

### contradiction_100 / 02b134ed-4f29-4b16-b338-25f71b94d8c5

Concept: Prediction If the comparison reveals that the government report s data and methodology are less rigorous than the scientific study s the government report

- Origin profile: `unknown`
- Provider: `qwen`
- First learned cycle: `23`
- Validation history: supported `1`, failed `0`, unresolved `0`
- Contradictions: `0`
- Redundancy: `0.0833`
- Projected centrality: `0.3433`
- Confidence trajectory: `[0.8, 0.8575]`
- Confidence slope: `0.0575`
- Supporting memories: `2`
- Supporting memory relationship edges: `1`
- Related concepts: `3`
- Prediction accuracy: `1.0`
- Final recommendation: `Promotion Eligible`

### planning_100 / 3761685d-98d0-4af8-b35c-742ad0b23f46

Concept: A prediction is that if the reallocation is not done promptly the number of unmet needs will increase resulting in higher stress levels and

- Origin profile: `resource_allocation`
- Provider: `qwen`
- First learned cycle: `21`
- Validation history: supported `1`, failed `0`, unresolved `0`
- Contradictions: `0`
- Redundancy: `0.16`
- Projected centrality: `0.3433`
- Confidence trajectory: `[0.8, 0.8575]`
- Confidence slope: `0.0575`
- Supporting memories: `2`
- Supporting memory relationship edges: `1`
- Related concepts: `3`
- Prediction accuracy: `1.0`
- Final recommendation: `Promotion Eligible`

### planning_100 / a626e504-dead-45cf-9dc7-43a58ae1dd1f

Concept: The cost records will guide the reallocation, but there is a risk of underfunding the ongoing needs of the current priority group

- Origin profile: `resource_allocation`
- Provider: `qwen`
- First learned cycle: `42`
- Validation history: supported `1`, failed `0`, unresolved `0`
- Contradictions: `0`
- Redundancy: `0.1818`
- Projected centrality: `0.2333`
- Confidence trajectory: `[0.8, 0.8575]`
- Confidence slope: `0.0575`
- Supporting memories: `2`
- Supporting memory relationship edges: `1`
- Related concepts: `1`
- Prediction accuracy: `1.0`
- Final recommendation: `Promotion Eligible`

### planning_200 / 9218afd4-0648-4298-b006-36f2aca23281

Concept: The tradeoff lies in the allocation of scarce capacity prioritizing immediate relief can lead to overburdened shelters and potential safety issues while a more

- Origin profile: `resource_allocation`
- Provider: `qwen`
- First learned cycle: `93`
- Validation history: supported `1`, failed `0`, unresolved `0`
- Contradictions: `0`
- Redundancy: `0.1471`
- Projected centrality: `0.2333`
- Confidence trajectory: `[0.8, 0.8575]`
- Confidence slope: `0.0575`
- Supporting memories: `2`
- Supporting memory relationship edges: `1`
- Related concepts: `1`
- Prediction accuracy: `1.0`
- Final recommendation: `Promotion Eligible`

### planning_200 / 7d3d6a2d-4a8b-4667-abe4-13297158d10f

Concept: Expected evidence includes log entries related to the incident, such as error messages, warnings, or unusual activity

- Origin profile: `tool_use`
- Provider: `qwen`
- First learned cycle: `7`
- Validation history: supported `1`, failed `0`, unresolved `0`
- Contradictions: `0`
- Redundancy: `0.08`
- Projected centrality: `0.3433`
- Confidence trajectory: `[0.8, 0.85]`
- Confidence slope: `0.05`
- Supporting memories: `2`
- Supporting memory relationship edges: `1`
- Related concepts: `3`
- Prediction accuracy: `1.0`
- Final recommendation: `Promotion Eligible`


## Promotion Survivor Similarities

- Count: `12`
- Providers: `{'qwen': 10, 'mistral': 1, 'llama': 1}`
- Profiles: `{'unknown': 5, 'resource_allocation': 3, 'risk_assessment': 1, 'contradiction': 1, 'negotiation': 1, 'tool_use': 1}`
- Average sentence length: `22.4167`
- Average supporting memories: `2.0`
- Average related concepts: `2.6667`
- Average redundancy: `0.1215`
- Average contradiction count: `0.0`
- Average projected centrality: `0.325`
- Average confidence slope: `0.0529`
- Average validation count: `1.0`
- Average prediction accuracy: `1.0`

## Bottom Reject Similarities

- Count: `10`
- Providers: `{'qwen': 5, 'llama': 4, 'mistral': 1}`
- Profiles: `{'negotiation': 4, 'tool_use': 2, 'resource_allocation': 2, 'hierarchical_planning': 1, 'contradiction': 1}`
- Average sentence length: `18.4`
- Average supporting memories: `2.0`
- Average related concepts: `2.9`
- Average redundancy: `0.5323`
- Average contradiction count: `0.0`
- Average projected centrality: `0.3538`
- Average confidence slope: `-0.089`
- Average validation count: `1.0`
- Average prediction accuracy: `0.0`

## Bottom Ten Rejects

| Run | Score | Provider | Profile | Origin Tick | Supported Predictions | Open Contradictions | Redundancy | Concept |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| broad_balanced_200 | 0.0 | llama | negotiation | 158 | 0 | 0 | 0.5 | Each party's likely belief and prediction about the other's response should be identified |
| broad_balanced_200 | 0.0 | qwen | tool_use | 190 | 0 | 0 | 0.28 | If the first result is contradicted for example if the missing field is found in the database snapshot belief revision w |
| broad_balanced_200 | 0.0 | qwen | hierarchical_planning | 126 | 0 | 0 | 0.2609 | The prediction is that power restoration will take longer than expected, and the evidence that would change the answer i |
| broad_balanced_100 | 0.0 | mistral | contradiction | 84 | 0 | 0 | 0.4667 | To resolve this, we can refer to the chain-of-custody notes, which document the handling and transmission of evidence |
| broad_balanced_100 | 0.0 | qwen | resource_allocation | 69 | 0 | 0 | 0.5 | When allocating resources for emergency shelters the tradeoff is between meeting the immediate needs of the priority gro |
| broad_balanced_200 | 0.0439 | qwen | tool_use | 120 | 0 | 0 | 0.4615 | Belief revision: If the first result from Tool A is contradicted, revise the belief to the second result from Tool B |
| broad_balanced_100 | 0.044 | qwen | resource_allocation | 78 | 0 | 0 | 0.5 | A tradeoff in allocating resources for emergency shelters must be made when the priority group changes |
| broad_balanced_200 | 0.0452 | llama | negotiation | 128 | 0 | 0 | 0.9167 | If Party A's cost estimate for a service is significantly |
| broad_balanced_100 | 0.0478 | llama | negotiation | 62 | 0 | 0 | 0.9375 | If Party A has a history of prioritizing cost over |
| broad_balanced_200 | 0.0495 | llama | negotiation | 138 | 0 | 0 | 0.5 | For instance if Party A s cost estimate for a particular service is significantly higher than their asking price it migh |

## Knowledge Survival Funnel

| Stage | Count |
| --- | ---: |
| generated | 812 |
| evaluated | 928 |
| validated_or_eligible | 460 |
| survived_contradiction_review | 859 |
| survived_redundancy_review | 769 |
| promotion_candidate_or_better | 831 |
| promotion_eligible | 12 |
| canonical_ready | 0 |

## State Transition Diagram

```text
Generated (812)
      |
      v
Evaluated (928)
      |
      v
Validated (448)
      |
  +---+----------------------+
  |                          |
  v                          v
Rejected (63)        Candidate (371)
                             |
                             v
Hold/Experimental (34)
                             |
                             v
Promotion Eligible (12)
                             |
                             v
Canonical Ready (0)
```

## Failure Cause Distribution

| Failure Cause | Count | Percent |
| --- | ---: | ---: |
| unresolved_predictions | 72 | 74.23 |
| failed_validation | 14 | 14.43 |
| high_redundancy | 9 | 9.28 |
| contradiction_pressure | 1 | 1.03 |
| low_composite_score | 1 | 1.03 |

## Survivor Maturation Time

- average_first_learned_cycle: `58.5`
- average_observed_cycles_to_final_eligibility: `67.1667`
- min_observed_cycles_to_final_eligibility: `0`
- max_observed_cycles_to_final_eligibility: `193`
- measurement_note: `Phase 26 stores final governance snapshots, not the exact cycle at which a concept first became Validated or Promotion Eligible. These are origin-to-final-governance maturation windows, not true state-transition timestamps.`

## Current-Concept Unresolved Prediction Taxonomy

This is the backlog that still attaches to current governance-visible concepts.

- `redundant_current_concept_backlog`: `22`
- `unvisited_current_concept_backlog`: `21`
- `late_cycle_current_concept_backlog`: `19`
- `partially_validated_current_concept_backlog`: `19`
- `incomplete_current_concept_backlog`: `2`
- `prompt_specific_current_concept_backlog`: `1`

## Raw Prediction Backlog Taxonomy

This includes predictions attached to superseded concept revisions and can exceed governance-pressure counts.

- `source_concept_missing_or_superseded`: `913`
- `never_revisited`: `107`

## Redundancy Taxonomy

- `accepted_overlap_reusable`: `239`
- `moderate_overlap_unmatured`: `196`
- `high_paraphrase_overlap`: `28`

## Contradiction Taxonomy

- `references_superseded_or_missing_concept`: `21`
- `resolved`: `2`

## Measurement Limitation

Phase 26 stored final governance decisions, not per-cycle promotion-score snapshots. Phase 27 reports origin-cycle velocity proxies and confidence trajectories, but not true promotion-score trajectories.

## Recommendation

Next work should audit semantic equivalence and merge candidates report-only, then schedule unresolved current-concept predictions for maturation; do not change canonical knowledge yet.
