# Runtime V1.3 Isolated Simulations

These simulations are read-only and do not modify Runtime V1.2 activation, attention, learning, or stores.

Final recommendation: `PROCEED_RECURRING_NOISE_SUPPRESSION_PROTOTYPE`

## Recurring-Noise Suppression Simulation

| Metric | Before | After |
| --- | ---: | ---: |
| expected outside top 10 | `7` | `6` |
| expected outside top 20 | `5` | `3` |
| mean expected rank | `10` | `7.2609` |
| mean noise above expected | `8.0435` | `5.3043` |

- expected top-10 concepts pushed out: `0`
- accepted: `True`

### Recurring Noisy Concepts Suppressed

- `cb4f7649-cbdd-4cb3-905d-6f5f69832e9c` in `10` case top-50 lists
- `0e3fdeda-0d38-40ad-993c-480703e55f9e` in `10` case top-50 lists
- `0586e881-099d-4866-a1cf-4ed571139c70` in `8` case top-50 lists
- `65e4ca55-7169-4ee4-b388-a6927043a92d` in `8` case top-50 lists
- `17a8d30a-9f2d-4d15-8100-d4bf18ca2e71` in `8` case top-50 lists
- `5252e50d-b97e-4d57-a79a-b9d64ddbbec7` in `8` case top-50 lists
- `e0038487-2363-4ba8-8e2e-a1b465c44ee0` in `8` case top-50 lists
- `89b85467-0655-47d3-9a0c-89da364cd487` in `8` case top-50 lists
- `5ac48263-cbff-4380-bf63-fc9500bcad8d` in `8` case top-50 lists
- `b85b0a01-9c3f-4c42-a26a-01741c84682c` in `8` case top-50 lists

## Sparse Abstention Gate Simulation

- sparse cases abstained: `none`
- false non-sparse abstentions: `none`
- accepted: `False`

| Case | Sparse Expected | Decision | Strongest Specific Signal | Best Meaningful Overlap |
| --- | --- | --- | ---: | ---: |
| planning_failed_assumption | `False` | `PASS` | `10` | `8` |
| causal_industrial_failure | `False` | `PASS` | `6` | `3` |
| contradictory_evidence | `False` | `PASS` | `4` | `3` |
| resource_allocation_shelters | `False` | `PASS` | `7` | `4` |
| risk_uncertainty_planning | `False` | `PASS` | `4` | `3` |
| policy_audit_conflict | `False` | `PASS` | `7` | `3` |
| multi_step_failure_revision | `False` | `PASS` | `5` | `5` |
| logistics_proxy_planning | `False` | `PASS` | `4` | `5` |
| sparse_violin_tuning | `True` | `PASS` | `1` | `0` |
| unsupported_recipe | `True` | `PASS` | `2` | `0` |

## Attention Rescue Simulation

- expected pruned: `9`
- expected rescued: `7`
- noise that would also be rescued: `41`
- projected noise_used_in_reasoning increase: `41`
- accepted: `False`

| Case | Pruned Expected | Expected Rescued | Noise Also Rescued |
| --- | ---: | ---: | ---: |
| planning_failed_assumption | `1` | `1` | `5` |
| causal_industrial_failure | `0` | `0` | `6` |
| contradictory_evidence | `3` | `3` | `5` |
| resource_allocation_shelters | `1` | `1` | `8` |
| risk_uncertainty_planning | `2` | `1` | `3` |
| policy_audit_conflict | `0` | `0` | `0` |
| multi_step_failure_revision | `1` | `1` | `4` |
| logistics_proxy_planning | `1` | `0` | `1` |
| sparse_violin_tuning | `0` | `0` | `0` |
| unsupported_recipe | `0` | `0` | `9` |

## Recommendation

Proceed with recurring-noise suppression as the next live prototype, guarded by the preserved V1.2 benchmark.

`PROCEED_RECURRING_NOISE_SUPPRESSION_PROTOTYPE`
