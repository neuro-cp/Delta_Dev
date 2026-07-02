# Runtime V1.3 Planning Support Scoring Simulation

Generated: `2026-07-02T13:47:16`

Report-only simulation. Model B remains default. No live runtime, learning, governance, storage, provider, activation, attention, candidate-store, or canonical behavior was modified.

## Baseline

| Metric | Model B | Variant C |
| --- | ---: | ---: |
| planning_score | `1.0` | `1.0` |
| planning_drift_cases | `1.0` | `2.0` |
| reasoning_drift_cases | `4.0` | `1.0` |
| noise_used_in_reasoning | `7.0` | `1.0` |
| citable_noise_used_in_reasoning | `None` | `1.0` |
| planning_support_count | `None` | `6.0` |
| planning_core_coverage | `0.4333` | `0.4333` |
| response_core_coverage | `0.4333` | `0.4333` |

## Model Results

| Model | Planning Drift | Reasoning Drift | Citable Noise | Support Count | Expected Lost | Noise Support Retained | Acceptance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| PS1 | `5` | `1` | `1` | `2` | `17` | `3` | `False` |
| PS2 | `4` | `1` | `1` | `20` | `14` | `15` | `False` |
| PS3 | `5` | `1` | `1` | `2` | `17` | `3` | `False` |
| PS4 | `4` | `4` | `1` | `5` | `17` | `6` | `False` |
| PS5 | `4` | `4` | `6` | `0` | `17` | `6` | `False` |

## Focus Case: causal_industrial_failure

| Model | Decision | Expected Retained | Expected Lost | Noise Support Retained | Noise Support Removed |
| --- | --- | --- | --- | --- | --- |
| PS1 | `Planning Drift` | `ce828fd3-8630-418e-857b-65904d4fb2ed, e3bd802d-b767-4d7d-9dd5-72fb30bd08ce` | `45d9686a-fded-4818-ae8e-47007cd33529` | `c5cc234b-b4ae-4f0c-98f7-c7f04e320abf` | `0fb23c0b-b877-4cf2-a66d-94d927b77542, 9d5b7363-5857-4091-8449-9374d6b4b68f` |
| PS2 | `Healthy` | `45d9686a-fded-4818-ae8e-47007cd33529, ce828fd3-8630-418e-857b-65904d4fb2ed, e3bd802d-b767-4d7d-9dd5-72fb30bd08ce` | `none` | `183718d2-9612-4057-94b7-4ad8fd896278, 7cc932e8-ccbf-47dc-8c14-8ac0dc3dd4c5, b1f3eca3-5024-45c1-a91d-68ef0d7d28e5` | `0fb23c0b-b877-4cf2-a66d-94d927b77542, 9d5b7363-5857-4091-8449-9374d6b4b68f, c5cc234b-b4ae-4f0c-98f7-c7f04e320abf` |
| PS3 | `Planning Drift` | `ce828fd3-8630-418e-857b-65904d4fb2ed, e3bd802d-b767-4d7d-9dd5-72fb30bd08ce` | `45d9686a-fded-4818-ae8e-47007cd33529` | `c5cc234b-b4ae-4f0c-98f7-c7f04e320abf` | `0fb23c0b-b877-4cf2-a66d-94d927b77542, 9d5b7363-5857-4091-8449-9374d6b4b68f` |
| PS4 | `Reasoning Drift` | `ce828fd3-8630-418e-857b-65904d4fb2ed, e3bd802d-b767-4d7d-9dd5-72fb30bd08ce` | `45d9686a-fded-4818-ae8e-47007cd33529` | `0fb23c0b-b877-4cf2-a66d-94d927b77542, 9d5b7363-5857-4091-8449-9374d6b4b68f, c5cc234b-b4ae-4f0c-98f7-c7f04e320abf` | `none` |
| PS5 | `Reasoning Drift` | `ce828fd3-8630-418e-857b-65904d4fb2ed, e3bd802d-b767-4d7d-9dd5-72fb30bd08ce` | `45d9686a-fded-4818-ae8e-47007cd33529` | `0fb23c0b-b877-4cf2-a66d-94d927b77542, 9d5b7363-5857-4091-8449-9374d6b4b68f, c5cc234b-b4ae-4f0c-98f7-c7f04e320abf` | `0fb23c0b-b877-4cf2-a66d-94d927b77542, 9d5b7363-5857-4091-8449-9374d6b4b68f, c5cc234b-b4ae-4f0c-98f7-c7f04e320abf` |

## Focus Case: policy_audit_conflict

| Model | Decision | Expected Retained | Expected Lost | Noise Support Retained |
| --- | --- | --- | --- | --- |
| PS1 | `Planning Drift` | `acaca659-aee5-4cef-9c4c-5a2281c1a9ef` | `1b324e50-0b5b-43b4-befd-f4e6e25d5e01, 3cc55e56-cb07-4085-a786-afd705a58770` | `none` |
| PS2 | `Planning Drift` | `1b324e50-0b5b-43b4-befd-f4e6e25d5e01, acaca659-aee5-4cef-9c4c-5a2281c1a9ef` | `3cc55e56-cb07-4085-a786-afd705a58770` | `none` |
| PS3 | `Planning Drift` | `acaca659-aee5-4cef-9c4c-5a2281c1a9ef` | `1b324e50-0b5b-43b4-befd-f4e6e25d5e01, 3cc55e56-cb07-4085-a786-afd705a58770` | `none` |
| PS4 | `Planning Drift` | `acaca659-aee5-4cef-9c4c-5a2281c1a9ef` | `1b324e50-0b5b-43b4-befd-f4e6e25d5e01, 3cc55e56-cb07-4085-a786-afd705a58770` | `none` |
| PS5 | `Planning Drift` | `acaca659-aee5-4cef-9c4c-5a2281c1a9ef` | `1b324e50-0b5b-43b4-befd-f4e6e25d5e01, 3cc55e56-cb07-4085-a786-afd705a58770` | `none` |

## PS2 Selected Candidates For causal_industrial_failure

| Selected | Eval Role | Score | Rank | Specific | Domain | Concrete | Broad | Text |
| ---: | --- | ---: | ---: | --- | --- | ---: | ---: | --- |
| `True` | `expected` | `1.7672` | `1` | `caus, industrial, maintenance` | `caus, cause, failure, industrial, maintenance` | `2` | `0` | In industrial maintenance, when two causes interact, a failure timeline can help identify the root cause by rejecting spurious ... |
| `False` | `expected` | `1.2872` | `2` | `caus, industrial, maintenance` | `caus, failure, industrial, maintenance` | `0` | `0` | In industrial maintenance, when two causes interact, a causal chain can be established by examining the failure timelines of th... |
| `True` | `noise` | `1.5032` | `3` | `caus, maintenance` | `caus, failure, maintenance` | `3` | `0` | For instance, if increased maintenance frequency is correlated with higher equipment failure rates, it might be tempting to con... |
| `True` | `noise` | `1.3598` | `5` | `maintenance` | `failure, maintenance` | `6` | `0` | This cycle can be completed by making a testable prediction: if the maintenance introduces stress, then reducing the frequency ... |
| `True` | `noise` | `1.184` | `30` | `maintenance` | `failure, maintenance` | `3` | `0` | For instance, if a machine's failure rate increases during specific maintenance intervals, it suggests that the maintenance its... |
| `True` | `expected` | `1.4839` | `37` | `maintenance` | `cause, failure, maintenance` | `8` | `0` | In this cycle the prediction is that if the maintenance frequency is increased further without addressing the root cause e g eq... |

## Interpretation

No model produced a clean enough projection. PS2 causal result: Healthy; PS3 causal result: Planning Drift.

## Boundary

This is not a runtime patch. Evaluation labels were used only to score simulated outputs after candidate selection, not as simulated live signals.

RUN_MORE_DIAGNOSTICS
