# Runtime V1.3 Query Decomposition Activation Simulation

Generated: `2026-07-02T14:37:08`

Report-only simulation. No runtime behavior, learning, validation, normalization, governance, storage, providers, candidate stores, canonical systems, benchmark fixtures, or default behavior was modified.

Current accepted default: Model B contextualized corpus support + citation_context reasoning usage gate

Final recommendation: `RUN_MORE_DIAGNOSTICS`

## Summary

This simulation decomposed each question into live-safe activation intents using question text only, then projected activation, attention, reasoning/citation use, planning, and response outcomes against archived Model B data.

## Why Relation-Aware Activation Failed

Relation-aware activation ended with `PROCEED_QUERY_DECOMPOSITION_ACTIVATION_SIMULATION`. It recovered more expected evidence, but relation frames applied to the full broad candidate pool still admitted same-topic wrong-relation noise.

## Decomposition Models Tested

- `QDA1`: single primary intent.
- `QDA2`: subject/domain, relation/action, evidence/outcome split.
- `QDA3`: relation-family first.
- `QDA4`: evidence-need first.
- `QDA5`: conservative hybrid intent scoring.
- `QDA6`: QDA5 visibility with separated reasoning/citation use.

## Model Comparison

| Model | Pass | Noise | Citable Noise | Reasoning Drift | Planning Drift | Plan Cov | Resp Cov | Improved | Regressed | Expected Recovered | Visible Expected | Same-Topic Noise |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| QDA1 | `False` | `9` | `9` | `7` | `0` | `0.6667` | `0.6667` | `1` | `3` | `14` | `19` | `9` |
| QDA2 | `False` | `9` | `9` | `7` | `0` | `0.6667` | `0.6667` | `1` | `3` | `14` | `18` | `9` |
| QDA3 | `False` | `12` | `12` | `7` | `0` | `0.6` | `0.6` | `1` | `3` | `12` | `21` | `12` |
| QDA4 | `False` | `13` | `13` | `7` | `0` | `0.5667` | `0.5667` | `1` | `3` | `11` | `18` | `13` |
| QDA5 | `False` | `14` | `14` | `7` | `0` | `0.5333` | `0.5333` | `1` | `3` | `10` | `21` | `14` |
| QDA6 | `False` | `2` | `2` | `2` | `5` | `0.5` | `0.5` | `2` | `2` | `9` | `21` | `2` |

## Query Decomposition Examples

- `planning_failed_assumption`: family `planning`, evidence need `revision_action`, subject cues `emergency`
- `causal_industrial_failure`: family `causal`, evidence need `revision_action`, subject cues `analyzed, causes, industrial, interacting`
- `contradictory_evidence`: family `contradiction`, evidence need `contradiction_resolution`, subject cues `contradictory, eyewitness, handled`
- `resource_allocation_shelters`: family `resource`, evidence need `resource_constraint`, subject cues `allocated, changes, emergency, resources`
- `risk_uncertainty_planning`: family `risk`, evidence need `risk_uncertainty`, subject cues `account`

## Case-Level Improvements/Regressions

### QDA1
- `planning_failed_assumption`: `Under-Attending` -> `Healthy`; expected recovered `3`, noise `0`
- `policy_audit_conflict`: `Planning Drift` -> `Reasoning Drift`; expected recovered `2`, noise `1`
- `multi_step_failure_revision`: `Under-Attending` -> `Reasoning Drift`; expected recovered `2`, noise `1`
- `logistics_proxy_planning`: `Under-Attending` -> `Reasoning Drift`; expected recovered `1`, noise `2`

### QDA2
- `planning_failed_assumption`: `Under-Attending` -> `Healthy`; expected recovered `3`, noise `0`
- `policy_audit_conflict`: `Planning Drift` -> `Reasoning Drift`; expected recovered `2`, noise `1`
- `multi_step_failure_revision`: `Under-Attending` -> `Reasoning Drift`; expected recovered `2`, noise `1`
- `logistics_proxy_planning`: `Under-Attending` -> `Reasoning Drift`; expected recovered `1`, noise `2`

### QDA3
- `planning_failed_assumption`: `Under-Attending` -> `Healthy`; expected recovered `3`, noise `0`
- `policy_audit_conflict`: `Planning Drift` -> `Reasoning Drift`; expected recovered `2`, noise `1`
- `multi_step_failure_revision`: `Under-Attending` -> `Reasoning Drift`; expected recovered `1`, noise `2`
- `logistics_proxy_planning`: `Under-Attending` -> `Reasoning Drift`; expected recovered `1`, noise `2`

### QDA4
- `planning_failed_assumption`: `Under-Attending` -> `Healthy`; expected recovered `3`, noise `0`
- `policy_audit_conflict`: `Planning Drift` -> `Reasoning Drift`; expected recovered `2`, noise `1`
- `multi_step_failure_revision`: `Under-Attending` -> `Reasoning Drift`; expected recovered `1`, noise `2`
- `logistics_proxy_planning`: `Under-Attending` -> `Reasoning Drift`; expected recovered `0`, noise `3`

### QDA5
- `planning_failed_assumption`: `Under-Attending` -> `Healthy`; expected recovered `3`, noise `0`
- `policy_audit_conflict`: `Planning Drift` -> `Reasoning Drift`; expected recovered `2`, noise `1`
- `multi_step_failure_revision`: `Under-Attending` -> `Reasoning Drift`; expected recovered `1`, noise `2`
- `logistics_proxy_planning`: `Under-Attending` -> `Reasoning Drift`; expected recovered `0`, noise `3`

### QDA6
- `planning_failed_assumption`: `Under-Attending` -> `Planning Drift`; expected recovered `2`, noise `0`
- `causal_industrial_failure`: `Reasoning Drift` -> `Planning Drift`; expected recovered `2`, noise `0`
- `contradictory_evidence`: `Reasoning Drift` -> `Planning Drift`; expected recovered `2`, noise `0`
- `multi_step_failure_revision`: `Under-Attending` -> `Planning Drift`; expected recovered `2`, noise `0`

## Sparse/Unsupported Safety

Sparse and unsupported cases are guarded by question-text cues only and remained acceptance gates for every model.

## Best Candidate

Passed candidates: `none`

## Rejected Candidates

- `QDA1` rejected: noise_no_increase, citable_noise_no_increase, reasoning_drift_no_increase
- `QDA2` rejected: noise_no_increase, citable_noise_no_increase, reasoning_drift_no_increase
- `QDA3` rejected: noise_no_increase, citable_noise_no_increase, reasoning_drift_no_increase
- `QDA4` rejected: noise_no_increase, citable_noise_no_increase, reasoning_drift_no_increase
- `QDA5` rejected: noise_no_increase, citable_noise_no_increase, reasoning_drift_no_increase
- `QDA6` rejected: planning_drift_no_increase

## Live Prototype

Should be attempted later: `False`

## Continuation Checkpoint

- Model B default remains active: `True`
- Runtime files modified: `False`
- Raw archive: `G:\Delta_Dev\reports\runtime_v13_query_decomposition_activation_raw`

RUN_MORE_DIAGNOSTICS
