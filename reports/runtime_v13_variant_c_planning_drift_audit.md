# Runtime V1.3 Variant C Planning-Drift Audit

Generated: `2026-07-02T13:39:34`

Diagnostic only. No runtime behavior, learning, governance, storage, activation, attention, provider, or canonical systems were modified.

## Aggregate Comparison

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
| attention_precision | `0.6333` | `0.64` |
| attention_recall | `0.4333` | `0.4333` |
| hallucinations | `0.0` | `0.0` |

## Drift Summary

- Model B planning drift cases: `['policy_audit_conflict']`
- Variant C planning drift cases: `['causal_industrial_failure', 'policy_audit_conflict']`
- New Variant C planning drift cases: `causal_industrial_failure`
- Shared planning drift cases: `policy_audit_conflict`

## New Planning-Drift Cases

### causal_industrial_failure

- Model B decision: `Reasoning Drift`
- Variant C decision: `Planning Drift`
- Model B noisy reasoning concepts: `4`
- Variant C noisy reasoning concepts: `0`
- Planning core coverage: `0.6667` -> `0.6667`
- Response core coverage: `0.6667` -> `0.6667`
- Primary cause: Variant C removed noisy reasoning/response citations that made Model B fail earlier as Reasoning Drift, exposing an existing incomplete planning-core coverage condition.

#### Concept Movement

- Variant C Core Evidence: `ce828fd3-8630-418e-857b-65904d4fb2ed, e3bd802d-b767-4d7d-9dd5-72fb30bd08ce`
- Variant C Planning Support: `0fb23c0b-b877-4cf2-a66d-94d927b77542, 9d5b7363-5857-4091-8449-9374d6b4b68f, c5cc234b-b4ae-4f0c-98f7-c7f04e320abf`
- Planning-only concepts: `0fb23c0b-b877-4cf2-a66d-94d927b77542, 9d5b7363-5857-4091-8449-9374d6b4b68f, c5cc234b-b4ae-4f0c-98f7-c7f04e320abf`
- Removed response citations: `0fb23c0b-b877-4cf2-a66d-94d927b77542, 9d5b7363-5857-4091-8449-9374d6b4b68f, c5cc234b-b4ae-4f0c-98f7-c7f04e320abf`
- Removed reasoning evidence: `0fb23c0b-b877-4cf2-a66d-94d927b77542, 183718d2-9612-4057-94b7-4ad8fd896278, 9d5b7363-5857-4091-8449-9374d6b4b68f, c5cc234b-b4ae-4f0c-98f7-c7f04e320abf`
- Expected missing from planning: `45d9686a-fded-4818-ae8e-47007cd33529`

#### Concepts

| Concept ID | Eval Role | Eval Class | Attn Class | Reasoned | Planned | Responded | Text |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| 0fb23c0b-b877-4cf2-a66d-94d927b77542 | noise | Noise | Core | False | True | False | The uncertainty in this scenario lies in the potential confounding variables and the complexity of real world industrial settings where m... |
| 183718d2-9612-4057-94b7-4ad8fd896278 | noise | Noise | Supporting | False | False | False | For instance, if increased maintenance frequency is correlated with higher equipment failure rates, it might be tempting to conclude that... |
| 45d9686a-fded-4818-ae8e-47007cd33529 | expected | None | None | False | False | False | In this cycle the prediction is that if the maintenance frequency is increased further without addressing the root cause e g equipment ag... |
| 4e03e42f-32c2-48fb-a9ac-5afea778a8f2 | useful_neighbor | None | None | False | False | False | Future observations that would change the conclusion include additional failure events that contradict the established timeline or eviden... |
| 9d5b7363-5857-4091-8449-9374d6b4b68f | noise | Noise | Core | False | True | False | The current understanding is that causal relationships in industrial maintenance are complex and can be influenced by various factors lea... |
| c5cc234b-b4ae-4f0c-98f7-c7f04e320abf | noise | Noise | Supporting | False | True | False | For instance if a maintenance team observes that a machine s downtime is correlated with a specific type of weather they might mistakenly... |
| ce828fd3-8630-418e-857b-65904d4fb2ed | expected | Core | Core | True | True | True | In industrial maintenance, when two causes interact, a failure timeline can help identify the root cause by rejecting spurious causes |
| e3bd802d-b767-4d7d-9dd5-72fb30bd08ce | expected | Core | Core | True | True | True | In industrial maintenance, when two causes interact, a causal chain can be established by examining the failure timelines of the componen... |
| e6f9a5a0-a724-48c4-ba2b-5d279555a25e | useful_neighbor | None | None | False | False | False | A prediction that would validate or falsify the system assumption is that after implementing failure drills the power grid will exhibit i... |

## Shared Planning-Drift Cases

- `policy_audit_conflict` stayed `Planning Drift`; planning core coverage `0.3333` -> `0.3333`.

## Interpretation

Variant C did not create a lower planning score and did not change aggregate planning-core coverage. The new planning-drift case is caused by removing noisy reasoning/response evidence that made Model B fail earlier as Reasoning Drift. Once that higher-priority reasoning failure is removed, the evaluator can see the existing partial planning-core coverage. In the new drift case, Variant C still permits evaluator-noise concepts into Planning Support, so the next step should be a scoring simulation for planning support rather than a live behavior patch.

## Smallest Safe Next Experiment

Run a report-only Planning Support scoring simulation that keeps Model B as the default, preserves response citation separation, and tests whether planning-support candidates can be scored to exclude evaluator-noise concepts while retaining expected planning coverage. Do not patch live runtime until the simulation shows planning_drift_cases does not regress.

PROCEED_PLANNING_SUPPORT_SCORING_SIMULATION
