# Runtime V1.3 Query-Relation Matching Simulation

Generated: `2026-07-02T13:52:38`

Report-only simulation. Model B remains default. No runtime behavior, activation, attention, learning, governance, storage, provider, candidate-store, or canonical systems were modified.

## Model Results

| Model | Focus Decision | Focus Recovered | Focus False Positives | Planning Drift | Reasoning Drift | Citable Noise | Acceptance |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| QRM1 | `Healthy` | `True` | `1` | `4` | `1` | `1` | `False` |
| QRM2 | `Healthy` | `True` | `1` | `4` | `1` | `1` | `False` |
| QRM3 | `Healthy` | `True` | `1` | `4` | `1` | `1` | `False` |
| QRM4 | `Healthy` | `True` | `0` | `4` | `1` | `1` | `False` |
| QRM5 | `Healthy` | `True` | `0` | `4` | `1` | `1` | `False` |

## Focus Case: causal_industrial_failure

| Model | Selected Support | Removed False Positives | Candidate Notes |
| --- | --- | --- | --- |
| QRM1 | `183718d2-9612-4057-94b7-4ad8fd896278, 45d9686a-fded-4818-ae8e-47007cd33529, ce828fd3-8630-418e-857b-65904d4fb2ed` | `7cc932e8-ccbf-47dc-8c14-8ac0dc3dd4c5, b1f3eca3-5024-45c1-a91d-68ef0d7d28e5` | ce828fd3-8630-418e-857b-65904d4fb2ed (expected, selected=True, slots=3, direction=False): In industrial maintenance, when two causes interact, a failure timeline can help identi...<br>183718d2-9612-4057-94b7-4ad8fd896278 (noise, selected=True, slots=4, direction=False): For instance, if increased maintenance frequency is correlated with higher equipment fa...<br>45d9686a-fded-4818-ae8e-47007cd33529 (expected, selected=True, slots=6, direction=True): In this cycle the prediction is that if the maintenance frequency is increased further ... |
| QRM2 | `45d9686a-fded-4818-ae8e-47007cd33529, b1f3eca3-5024-45c1-a91d-68ef0d7d28e5` | `183718d2-9612-4057-94b7-4ad8fd896278, 7cc932e8-ccbf-47dc-8c14-8ac0dc3dd4c5` | ce828fd3-8630-418e-857b-65904d4fb2ed (expected, selected=False, slots=3, direction=False): In industrial maintenance, when two causes interact, a failure timeline can help identi...<br>b1f3eca3-5024-45c1-a91d-68ef0d7d28e5 (noise, selected=True, slots=4, direction=False): This cycle can be completed by making a testable prediction: if the maintenance introdu...<br>45d9686a-fded-4818-ae8e-47007cd33529 (expected, selected=True, slots=6, direction=True): In this cycle the prediction is that if the maintenance frequency is increased further ... |
| QRM3 | `45d9686a-fded-4818-ae8e-47007cd33529, b1f3eca3-5024-45c1-a91d-68ef0d7d28e5` | `183718d2-9612-4057-94b7-4ad8fd896278, 7cc932e8-ccbf-47dc-8c14-8ac0dc3dd4c5` | ce828fd3-8630-418e-857b-65904d4fb2ed (expected, selected=False, slots=3, direction=False): In industrial maintenance, when two causes interact, a failure timeline can help identi...<br>b1f3eca3-5024-45c1-a91d-68ef0d7d28e5 (noise, selected=True, slots=4, direction=False): This cycle can be completed by making a testable prediction: if the maintenance introdu...<br>45d9686a-fded-4818-ae8e-47007cd33529 (expected, selected=True, slots=6, direction=True): In this cycle the prediction is that if the maintenance frequency is increased further ... |
| QRM4 | `45d9686a-fded-4818-ae8e-47007cd33529` | `183718d2-9612-4057-94b7-4ad8fd896278, 7cc932e8-ccbf-47dc-8c14-8ac0dc3dd4c5, b1f3eca3-5024-45c1-a91d-68ef0d7d28e5` | ce828fd3-8630-418e-857b-65904d4fb2ed (expected, selected=False, slots=3, direction=False): In industrial maintenance, when two causes interact, a failure timeline can help identi...<br>45d9686a-fded-4818-ae8e-47007cd33529 (expected, selected=True, slots=6, direction=True): In this cycle the prediction is that if the maintenance frequency is increased further ... |
| QRM5 | `45d9686a-fded-4818-ae8e-47007cd33529` | `183718d2-9612-4057-94b7-4ad8fd896278, 7cc932e8-ccbf-47dc-8c14-8ac0dc3dd4c5, b1f3eca3-5024-45c1-a91d-68ef0d7d28e5` | ce828fd3-8630-418e-857b-65904d4fb2ed (expected, selected=False, slots=3, direction=False): In industrial maintenance, when two causes interact, a failure timeline can help identi...<br>45d9686a-fded-4818-ae8e-47007cd33529 (expected, selected=True, slots=6, direction=True): In this cycle the prediction is that if the maintenance frequency is increased further ... |

## Acceptance Checks

| Model | Failed Checks |
| --- | --- |
| QRM1 | `focus_false_positive_support_zero, planning_drift_no_increase_vs_model_b` |
| QRM2 | `focus_false_positive_support_zero, planning_drift_no_increase_vs_model_b` |
| QRM3 | `focus_false_positive_support_zero, planning_drift_no_increase_vs_model_b` |
| QRM4 | `planning_drift_no_increase_vs_model_b` |
| QRM5 | `planning_drift_no_increase_vs_model_b` |

## Interpretation

At least one relation model recovered the focus expected concept, but none satisfied all projected acceptance gates. Recovered focus concept models: QRM1, QRM2, QRM3, QRM4, QRM5.

Evaluation labels were used only after candidate selection to assess separation. The simulated relation filters use text, relation terms, domain terms, and generic-anchor ratios only.

RUN_MORE_DIAGNOSTICS
