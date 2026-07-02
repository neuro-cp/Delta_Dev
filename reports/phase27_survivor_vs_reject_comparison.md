# Phase 27 Survivor vs Reject Comparison

## Promotion Survivors

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

## Bottom Rejects

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
