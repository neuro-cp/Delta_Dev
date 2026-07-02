# Runtime V1.3 Bounded Attention Rescue Simulation

Generated: `2026-07-02T14:08:25`

Report-only simulation. No runtime behavior, learning, governance, storage, provider, activation, attention, candidate-store, or canonical systems were modified.

## Summary

- Current accepted default: Model B contextualized corpus support + citation_context reasoning usage gate
- Final recommendation: `PROCEED_ACTIVATION_RERANKING_SIMULATION`

## Model Comparison

| Model | Expected Rescued | Noise Rescued | Attention Recall | Attention Precision | Reasoning Drift | Planning Drift | Noise Used | Improved | Regressed | Acceptance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BAR1 | `4` | `8` | `0.4583` | `0.3333` | `6` | `1` | `15` | `1` | `2` | `False` |
| BAR2 | `5` | `4` | `0.5` | `0.5556` | `4` | `3` | `11` | `1` | `2` | `False` |
| BAR3 | `2` | `6` | `0.375` | `0.25` | `7` | `0` | `13` | `1` | `3` | `False` |
| BAR4 | `6` | `11` | `0.5417` | `0.3529` | `8` | `0` | `18` | `0` | `4` | `False` |
| BAR5 | `2` | `5` | `0.375` | `0.2857` | `7` | `0` | `12` | `1` | `3` | `False` |

## Rescued Expected Concepts

### BAR1
- `planning_failed_assumption`: `d9ba0c9f-f458-4512-a0e3-40892ef333b6`
- `contradictory_evidence`: `8430c4bb-9070-4e98-aaa6-90404f2da021`
- `contradictory_evidence`: `a1e249bd-67dc-4056-9120-89380cbe5928`
- `resource_allocation_shelters`: `df85054d-ffcd-4c50-8118-ecb512271eaf`

### BAR2
- `planning_failed_assumption`: `d9ba0c9f-f458-4512-a0e3-40892ef333b6`
- `contradictory_evidence`: `8430c4bb-9070-4e98-aaa6-90404f2da021`
- `contradictory_evidence`: `a1e249bd-67dc-4056-9120-89380cbe5928`
- `resource_allocation_shelters`: `df85054d-ffcd-4c50-8118-ecb512271eaf`
- `risk_uncertainty_planning`: `98154cbb-a296-4bc9-87e5-83e1e6fbd245`

### BAR3
- `planning_failed_assumption`: `d9ba0c9f-f458-4512-a0e3-40892ef333b6`
- `contradictory_evidence`: `a1e249bd-67dc-4056-9120-89380cbe5928`

### BAR4
- `planning_failed_assumption`: `d9ba0c9f-f458-4512-a0e3-40892ef333b6`
- `contradictory_evidence`: `0249542c-c698-4a93-805c-8f83c40f8c34`
- `contradictory_evidence`: `8430c4bb-9070-4e98-aaa6-90404f2da021`
- `contradictory_evidence`: `a1e249bd-67dc-4056-9120-89380cbe5928`
- `resource_allocation_shelters`: `df85054d-ffcd-4c50-8118-ecb512271eaf`
- `logistics_proxy_planning`: `380b765f-ffa2-4296-a66e-527bacb75a64`

### BAR5
- `planning_failed_assumption`: `d9ba0c9f-f458-4512-a0e3-40892ef333b6`
- `contradictory_evidence`: `a1e249bd-67dc-4056-9120-89380cbe5928`

## Rescued Noise Concepts

- `BAR1`: `8`
- `BAR2`: `4`
- `BAR3`: `6`
- `BAR4`: `11`
- `BAR5`: `5`

## Case-Level Improvements/Regressions

| Model | Case | Baseline | Projected | Rescued Expected | Rescued Noise |
| --- | --- | --- | --- | --- | --- |
| BAR1 | planning_failed_assumption | `Under-Attending` | `Healthy` | `d9ba0c9f-f458-4512-a0e3-40892ef333b6` | `none` |
| BAR1 | contradictory_evidence | `Reasoning Drift` | `Reasoning Drift` | `8430c4bb-9070-4e98-aaa6-90404f2da021, a1e249bd-67dc-4056-9120-89380cbe5928` | `1450511f-f0dd-4e2f-8598-1cf1511a2811` |
| BAR1 | resource_allocation_shelters | `Reasoning Drift` | `Reasoning Drift` | `df85054d-ffcd-4c50-8118-ecb512271eaf` | `2ecb3022-1ce7-46e9-b1e5-4da1ffd0ac7d, 6b704bd9-ecc5-4066-b351-a4eda0ba5c8d, bc2086b3-87d9-479a-935f-805fe7d523c7` |
| BAR1 | risk_uncertainty_planning | `Reasoning Drift` | `Reasoning Drift` | `none` | `cb4f7649-cbdd-4cb3-905d-6f5f69832e9c` |
| BAR1 | multi_step_failure_revision | `Under-Attending` | `Reasoning Drift` | `none` | `5ac48263-cbff-4380-bf63-fc9500bcad8d, e0038487-2363-4ba8-8e2e-a1b465c44ee0` |
| BAR1 | logistics_proxy_planning | `Under-Attending` | `Reasoning Drift` | `none` | `06b4d255-58d5-49f5-adec-43426ce0d09b` |
| BAR2 | planning_failed_assumption | `Under-Attending` | `Healthy` | `d9ba0c9f-f458-4512-a0e3-40892ef333b6` | `none` |
| BAR2 | contradictory_evidence | `Reasoning Drift` | `Reasoning Drift` | `8430c4bb-9070-4e98-aaa6-90404f2da021, a1e249bd-67dc-4056-9120-89380cbe5928` | `1450511f-f0dd-4e2f-8598-1cf1511a2811` |
| BAR2 | resource_allocation_shelters | `Reasoning Drift` | `Reasoning Drift` | `df85054d-ffcd-4c50-8118-ecb512271eaf` | `2ecb3022-1ce7-46e9-b1e5-4da1ffd0ac7d, 6b704bd9-ecc5-4066-b351-a4eda0ba5c8d, 97190912-de2a-4fa6-b283-a9a1baafb53c` |
| BAR2 | risk_uncertainty_planning | `Reasoning Drift` | `Reasoning Drift` | `98154cbb-a296-4bc9-87e5-83e1e6fbd245` | `none` |
| BAR2 | multi_step_failure_revision | `Under-Attending` | `Planning Drift` | `none` | `none` |
| BAR2 | logistics_proxy_planning | `Under-Attending` | `Planning Drift` | `none` | `none` |
| BAR3 | planning_failed_assumption | `Under-Attending` | `Healthy` | `d9ba0c9f-f458-4512-a0e3-40892ef333b6` | `none` |
| BAR3 | causal_industrial_failure | `Reasoning Drift` | `Reasoning Drift` | `none` | `65e4ca55-7169-4ee4-b388-a6927043a92d` |
| BAR3 | contradictory_evidence | `Reasoning Drift` | `Reasoning Drift` | `a1e249bd-67dc-4056-9120-89380cbe5928` | `none` |
| BAR3 | resource_allocation_shelters | `Reasoning Drift` | `Reasoning Drift` | `none` | `6b704bd9-ecc5-4066-b351-a4eda0ba5c8d` |
| BAR3 | risk_uncertainty_planning | `Reasoning Drift` | `Reasoning Drift` | `none` | `d9ba0c9f-f458-4512-a0e3-40892ef333b6` |
| BAR3 | policy_audit_conflict | `Planning Drift` | `Reasoning Drift` | `none` | `17a8d30a-9f2d-4d15-8100-d4bf18ca2e71` |
| BAR3 | multi_step_failure_revision | `Under-Attending` | `Reasoning Drift` | `none` | `3a9f7658-b877-4532-b9c8-1a79b360c5d4` |
| BAR3 | logistics_proxy_planning | `Under-Attending` | `Reasoning Drift` | `none` | `0586e881-099d-4866-a1cf-4ed571139c70` |
| BAR4 | planning_failed_assumption | `Under-Attending` | `Reasoning Drift` | `d9ba0c9f-f458-4512-a0e3-40892ef333b6` | `076c39f2-9cf5-45c7-ac1b-e379da875926` |
| BAR4 | contradictory_evidence | `Reasoning Drift` | `Reasoning Drift` | `0249542c-c698-4a93-805c-8f83c40f8c34, 8430c4bb-9070-4e98-aaa6-90404f2da021, a1e249bd-67dc-4056-9120-89380cbe5928` | `1450511f-f0dd-4e2f-8598-1cf1511a2811, 5ac48263-cbff-4380-bf63-fc9500bcad8d, 800c60da-06fc-41b6-b259-b4f98e08cd79, fb9f365a-95c7-4757-92f6-e55f4580c57b` |
| BAR4 | resource_allocation_shelters | `Reasoning Drift` | `Reasoning Drift` | `df85054d-ffcd-4c50-8118-ecb512271eaf` | `2ecb3022-1ce7-46e9-b1e5-4da1ffd0ac7d, 6b704bd9-ecc5-4066-b351-a4eda0ba5c8d, 97190912-de2a-4fa6-b283-a9a1baafb53c` |
| BAR4 | policy_audit_conflict | `Planning Drift` | `Reasoning Drift` | `none` | `5ac48263-cbff-4380-bf63-fc9500bcad8d` |
| BAR4 | multi_step_failure_revision | `Under-Attending` | `Reasoning Drift` | `none` | `5ac48263-cbff-4380-bf63-fc9500bcad8d` |
| BAR4 | logistics_proxy_planning | `Under-Attending` | `Reasoning Drift` | `380b765f-ffa2-4296-a66e-527bacb75a64` | `2ecb3022-1ce7-46e9-b1e5-4da1ffd0ac7d` |
| BAR5 | planning_failed_assumption | `Under-Attending` | `Healthy` | `d9ba0c9f-f458-4512-a0e3-40892ef333b6` | `none` |
| BAR5 | contradictory_evidence | `Reasoning Drift` | `Reasoning Drift` | `a1e249bd-67dc-4056-9120-89380cbe5928` | `none` |
| BAR5 | resource_allocation_shelters | `Reasoning Drift` | `Reasoning Drift` | `none` | `6b704bd9-ecc5-4066-b351-a4eda0ba5c8d` |
| BAR5 | risk_uncertainty_planning | `Reasoning Drift` | `Reasoning Drift` | `none` | `d9ba0c9f-f458-4512-a0e3-40892ef333b6` |
| BAR5 | policy_audit_conflict | `Planning Drift` | `Reasoning Drift` | `none` | `17a8d30a-9f2d-4d15-8100-d4bf18ca2e71` |
| BAR5 | multi_step_failure_revision | `Under-Attending` | `Reasoning Drift` | `none` | `3a9f7658-b877-4532-b9c8-1a79b360c5d4` |
| BAR5 | logistics_proxy_planning | `Under-Attending` | `Reasoning Drift` | `none` | `0586e881-099d-4866-a1cf-4ed571139c70` |

## Sparse/Unsupported Safety

No sparse/unsupported regressions were projected by this report-only simulation.

## Best Candidate

Bounded attention rescue is not clean enough: it either rescues noise alongside expected concepts or fails to move the dominant availability bottleneck. The next safer upstream test is activation reranking rather than broader attention rescue.

## Rejected Paths

- more Planning Support/QRM variants
- activation recurrence by default
- broad activation-window expansion
- evaluator-label, benchmark-case, or concept-ID live logic
- global threshold loosening

PROCEED_ACTIVATION_RERANKING_SIMULATION
