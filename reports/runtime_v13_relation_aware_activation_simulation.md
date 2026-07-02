# Runtime V1.3 Relation-Aware Activation Simulation

Generated: `2026-07-02T14:32:01`

Report-only simulation. No runtime behavior, learning, governance, storage, provider, candidate-store, canonical, benchmark, or default behavior was modified.

Current accepted default: Model B contextualized corpus support + citation_context reasoning usage gate

Final recommendation: `PROCEED_QUERY_DECOMPOSITION_ACTIVATION_SIMULATION`

## Why Prior Reranking Failed

Autonomous stabilizer result: `PROCEED_DEEP_ACTIVATION_DIAGNOSTICS`. Prior ARR variants admitted same-topic noise into reasoning.

## Model Comparison

| Model | Pass | Noise | Citable Noise | Reasoning Drift | Planning Drift | Plan Cov | Resp Cov | Improved | Regressed | Expected Recovered | Same-Topic Noise |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| RAA1 | `False` | `20` | `20` | `6` | `2` | `0.6333` | `0.6333` | `0` | `3` | `13` | `19` |
| RAA2 | `False` | `19` | `19` | `6` | `2` | `0.6` | `0.6` | `0` | `3` | `12` | `19` |
| RAA3 | `False` | `19` | `19` | `7` | `1` | `0.6` | `0.6` | `0` | `4` | `12` | `19` |
| RAA4 | `False` | `17` | `17` | `6` | `2` | `0.6` | `0.6` | `0` | `3` | `12` | `17` |
| RAA5 | `False` | `30` | `30` | `7` | `1` | `0.6333` | `0.6333` | `0` | `3` | `13` | `29` |
| RAA6 | `False` | `33` | `33` | `8` | `0` | `0.6667` | `0.6667` | `0` | `4` | `14` | `31` |

## Case-Level Improvements/Regressions

### RAA1
- `planning_failed_assumption`: `Under-Attending` -> `Reasoning Drift`
- `multi_step_failure_revision`: `Under-Attending` -> `Reasoning Drift`
- `logistics_proxy_planning`: `Under-Attending` -> `Planning Drift`

### RAA2
- `planning_failed_assumption`: `Under-Attending` -> `Reasoning Drift`
- `multi_step_failure_revision`: `Under-Attending` -> `Reasoning Drift`
- `logistics_proxy_planning`: `Under-Attending` -> `Planning Drift`

### RAA3
- `planning_failed_assumption`: `Under-Attending` -> `Reasoning Drift`
- `policy_audit_conflict`: `Planning Drift` -> `Reasoning Drift`
- `multi_step_failure_revision`: `Under-Attending` -> `Reasoning Drift`
- `logistics_proxy_planning`: `Under-Attending` -> `Planning Drift`

### RAA4
- `planning_failed_assumption`: `Under-Attending` -> `Reasoning Drift`
- `multi_step_failure_revision`: `Under-Attending` -> `Reasoning Drift`
- `logistics_proxy_planning`: `Under-Attending` -> `Planning Drift`

### RAA5
- `planning_failed_assumption`: `Under-Attending` -> `Reasoning Drift`
- `multi_step_failure_revision`: `Under-Attending` -> `Reasoning Drift`
- `logistics_proxy_planning`: `Under-Attending` -> `Reasoning Drift`

### RAA6
- `planning_failed_assumption`: `Under-Attending` -> `Reasoning Drift`
- `policy_audit_conflict`: `Planning Drift` -> `Reasoning Drift`
- `multi_step_failure_revision`: `Under-Attending` -> `Reasoning Drift`
- `logistics_proxy_planning`: `Under-Attending` -> `Reasoning Drift`

## Sparse/Unsupported Safety

Sparse and unsupported cases remained part of every acceptance gate.

## Live Prototype

Should be attempted later: `False`

## Continuation Checkpoint

- Model B default remains active: `True`
- Runtime files modified: `False`
- Raw archive: `G:\Delta_Dev\reports\runtime_v13_relation_aware_activation_raw`

PROCEED_QUERY_DECOMPOSITION_ACTIVATION_SIMULATION
