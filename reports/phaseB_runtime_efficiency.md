# Phase B.1 Runtime Efficiency

## Summary

| Metric | Value |
| --- | ---: |
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

## Interpretation

- Is low retrieval precision harming Runtime? `not materially harmful in this suite`
- Extra activated concepts are mostly: `mostly supportive neighbors`
- Is Working Memory carrying unnecessary load? `acceptable`
- Should retrieval ranking be optimized now? `no`
- Conversation testing recommendation: `reasonable after adding held-out prompts`

Attention keeps noisy activations out of downstream reasoning while preserving expected concepts.

## Per Case

| Case | Activated | Used | Ignored | Attention Precision | Attention Recall | Used Noise | Suppressed Core |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| gps_drift_retrieval | `4` | `3` | `1` | `1.0` | `1.0` | `0` | `0` |
| snowstorm_grounded_planning | `5` | `3` | `2` | `1.0` | `1.0` | `0` | `0` |
| salt_tradeoff_conflict | `6` | `2` | `4` | `1.0` | `1.0` | `0` | `0` |
| resource_allocation_calibration | `6` | `3` | `3` | `1.0` | `1.0` | `0` | `0` |
| sparse_violin_question | `0` | `0` | `0` | `1.0` | `1.0` | `0` | `0` |
| repeat_snowstorm_stability | `5` | `3` | `2` | `1.0` | `1.0` | `0` | `0` |
