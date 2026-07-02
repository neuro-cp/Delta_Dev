# Runtime V1.3 Attention-Gating Design

Final recommendation: `SIMULATE_REASONING_USAGE_GATE`

## Baseline Failure Summary

The rejected prototype improved activation rank metrics but admitted replacement noise through attention, increasing reasoning consumption of noisy concepts.

| Metric | Baseline | Rejected Prototype |
| --- | ---: | ---: |
| attention_precision | `0.55` | `0.4172` |
| attention_recall | `0.4333` | `0.4667` |
| expected_outside_top10 | `8` | `7` |
| expected_outside_top20 | `6` | `4` |
| grounding_score | `1.0` | `1.0` |
| hallucinations | `0.0` | `0.0` |
| mean_expected_rank | `10` | `7.1739` |
| mean_noise_above_expected | `9.7083` | `7` |
| noise_used_in_reasoning | `12.0` | `24.0` |
| read_only_verified | `True` | `True` |
| reasoning_drift_cases | `5.0` | `8.0` |
| retrieval_precision | `0.16` | `0.17` |
| retrieval_recall | `0.5333` | `0.5667` |

## Newly Used Noisy Concepts By Case

| Case | High Risk | Noise Delta | Concept | Attention Class | Attention Score | Query Overlap | Reasoned | Planned | Responded |
| --- | --- | ---: | --- | --- | ---: | --- | --- | --- | --- |
| causal_industrial_failure | `False` | `1` | `48c454a5-6362-4533-a53e-b6d6f9c19a00` | `Supporting` | `0.3514` | maintenance | `True` | `False` | `False` |
| contradictory_evidence | `False` | `1` | `011d4f3b-e7d2-4865-9fe3-b269795e07cb` | `Supporting` | `0.4853` | conflicting, reports | `True` | `True` | `True` |
| logistics_proxy_planning | `True` | `1` | `0121143f-0779-4965-9405-2e7b3eabcd05` | `Supporting` | `0.4836` | capacity, resource | `True` | `True` | `True` |
| multi_step_failure_revision | `False` | `0` | none | - | - | - | - | - | - |
| planning_failed_assumption | `True` | `1` | `e6f9a5a0-a724-48c4-ba2b-5d279555a25e` | `Supporting` | `0.4518` | after, assumption | `True` | `True` | `True` |
| policy_audit_conflict | `True` | `1` | `5894bef8-228f-4466-9152-cf7dfec7fa4e` | `Supporting` | `0.4981` | audit, policy | `True` | `True` | `True` |
| resource_allocation_shelters | `False` | `0` | none | - | - | - | - | - | - |
| risk_uncertainty_planning | `True` | `7` | `0ada7d73-b196-40cc-b6bb-031ac1eaa8cd` | `Supporting` | `0.3372` | and, should, uncertainty | `True` | `False` | `False` |
| risk_uncertainty_planning | `True` | `7` | `16ce389d-1c43-4d03-94e3-f16ad8259cbc` | `Core` | `0.4612` | plan, uncertainty | `True` | `True` | `True` |
| risk_uncertainty_planning | `True` | `7` | `6457f783-957c-4e69-95bb-bacf18f6fd32` | `Supporting` | `0.3389` | and, for, plan | `True` | `False` | `False` |
| risk_uncertainty_planning | `True` | `7` | `7b1fd455-c6f7-4dcf-a109-11fc3c89262f` | `Supporting` | `0.3389` | and, failure, for | `True` | `False` | `False` |
| risk_uncertainty_planning | `True` | `7` | `ad599dfe-ddbd-4689-ad43-4dc8249fdab1` | `Core` | `0.4608` | and, failure, risk | `True` | `True` | `True` |
| risk_uncertainty_planning | `True` | `7` | `d9ba0c9f-f458-4512-a0e3-40892ef333b6` | `Core` | `0.4589` | for, plan, risk, should | `True` | `True` | `True` |
| risk_uncertainty_planning | `True` | `7` | `fec7285c-8ebf-45ba-8197-911a515e4e0b` | `Core` | `0.4549` | and, failure, risk | `True` | `False` | `False` |
| sparse_violin_tuning | `False` | `0` | none | - | - | - | - | - | - |
| unsupported_recipe | `False` | `0` | none | - | - | - | - | - | - |

## Attention Classifications That Admitted Noise

- `Core`: `4`
- `Supporting`: `8`

## Query-Overlap Signals That Admitted Noise

- `and`: `5`
- `plan`: `3`
- `for`: `3`
- `failure`: `3`
- `risk`: `3`
- `should`: `2`
- `uncertainty`: `2`
- `maintenance`: `1`
- `conflicting`: `1`
- `reports`: `1`
- `capacity`: `1`
- `resource`: `1`
- `after`: `1`
- `assumption`: `1`
- `audit`: `1`
- `policy`: `1`

## Proposed Gating Strategies

### A. Recurrence-risk metadata only

Expose recurrence-risk and weak-specificity flags in attention traces without changing selection.

- would block newly used noise: `0`
- coverage of newly used noise: `0.0`
- regression risk: `lowest`
- assessment: Useful instrumentation, but insufficient as the next prototype because it cannot reduce noise consumption.

### B. Negative attention feature

Subtract a bounded attention penalty when recurrence-risk or replacement-risk combines with weak specific query overlap.

- would block newly used noise: `6`
- coverage of newly used noise: `0.5`
- regression risk: `medium`
- assessment: Good candidate, but it changes selection and could repeat the activation-prototype mistake at the attention layer.

### C. Usage gate before reasoning

Allow weak replacement-risk candidates into working memory for observability, but prevent reasoning from consuming them unless they have stronger support than shallow query overlap.

- would block newly used noise: `6`
- coverage of newly used noise: `0.5`
- regression risk: `low-medium`
- assessment: Best next simulation because the observed failure is not retrieval presence; it is noisy concepts entering reasoning.

### D. Supporting-only downgrade

Downgrade weak replacement-risk Core/Supporting concepts to Peripheral before reasoning.

- would block newly used noise: `12`
- coverage of newly used noise: `1.0`
- regression risk: `medium`
- assessment: Potentially equivalent to a hard attention penalty unless carefully limited to usage, not visibility.

### E. Case-local replacement-noise guard

For concepts that newly entered activation top-10 after recurring concepts were suppressed, require stronger query specificity before attention selection.

- would block newly used noise: `7`
- coverage of newly used noise: `0.5833`
- regression risk: `medium-high`
- assessment: Explains the failure but is too coupled to the rejected activation mutation to be the first live design.

## Predicted Effects

### A. Recurrence-risk metadata only
- `attention_precision`: unchanged
- `attention_recall`: unchanged
- `noise_used_in_reasoning`: unchanged
- `planning_core_coverage`: unchanged
- `response_core_coverage`: unchanged
- `grounding_score`: unchanged
- `hallucinations`: unchanged

### B. Negative attention feature
- `attention_precision`: likely improves
- `attention_recall`: possible mild regression if expected concepts have sparse overlap
- `noise_used_in_reasoning`: likely decreases
- `planning_core_coverage`: watch for under-attending
- `response_core_coverage`: watch for under-attending
- `grounding_score`: should remain stable
- `hallucinations`: should remain 0 if response remains evidence bounded

### C. Usage gate before reasoning
- `attention_precision`: selection metric may remain similar
- `attention_recall`: selection recall should remain stable
- `noise_used_in_reasoning`: likely decreases sharply
- `planning_core_coverage`: lower risk than selection penalty because core concepts remain visible
- `response_core_coverage`: lower risk than selection penalty because core concepts remain visible
- `grounding_score`: should remain stable
- `hallucinations`: should remain 0 if response still cites used evidence only

### D. Supporting-only downgrade
- `attention_precision`: likely improves if Peripheral is not counted as attended
- `attention_recall`: possible regression on sparse expected concepts
- `noise_used_in_reasoning`: likely decreases
- `planning_core_coverage`: watch expected Supporting concepts
- `response_core_coverage`: watch expected Supporting concepts
- `grounding_score`: should remain stable
- `hallucinations`: should remain 0

### E. Case-local replacement-noise guard
- `attention_precision`: likely improves in affected cases
- `attention_recall`: unknown until expected concepts newly entering top-10 are checked
- `noise_used_in_reasoning`: likely decreases in up to 6 noisy cases
- `planning_core_coverage`: requires simulation
- `response_core_coverage`: requires simulation
- `grounding_score`: should remain stable
- `hallucinations`: should remain 0

## Regression Risks

- Over-gating could suppress sparse but valid expected concepts before they influence reasoning.
- A negative attention feature could recreate the live-prototype failure if it changes selection without checking downstream use.
- Usage gating could preserve attention recall but make planning appear to ignore visible supporting evidence if reports do not distinguish visible from usable.
- Hard discard would hide diagnostic evidence and make future activation failures harder to explain.
- Query-overlap rules are brittle because broad terms such as risk, evidence, plan, resource, and failure can be legitimate anchors.

## Recommended Next Simulation

Replay the V1.2/V1.3 contribution traces with a read-only usage gate: recurrence-risk or replacement-risk plus weak specificity remains visible in working memory but cannot contribute to reasoning, planning, or response unless stronger evidence support is present.

## Explicitly Rejected Strategies

- global attention threshold loosening
- stronger activation recurrence penalty
- hard concept blacklist
- learning/governance/promotion changes
- provider prompt changes

`SIMULATE_REASONING_USAGE_GATE`
