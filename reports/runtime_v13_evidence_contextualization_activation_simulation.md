# Runtime V1.3 Evidence Contextualization Activation Simulation

Generated: `2026-07-02T14:52:35`

Report-only simulation. No runtime behavior, learning, validation, normalization, governance, storage, providers, candidate stores, canonical systems, benchmark fixtures, or default behavior was modified.

Current accepted default: Model B contextualized corpus support + citation_context reasoning usage gate

Final recommendation: `RUN_MORE_DIAGNICS`

## Summary

This simulation adds query-specific evidence context during activation, then projects unchanged citation-gate outcomes.

## Why Citation-Gate Review Failed

Citation-gate review ended with `PROCEED_EVIDENCE_CONTEXTUALIZATION_IN_ACTIVATION_SIMULATION` because relaxing the gate admitted expected evidence and same-topic noise together.

## Evidence-Contextualization Models Tested

- `ECA1`: evidence-need context.
- `ECA2`: query-concept context bridge.
- `ECA3`: contextualized citation preview.
- `ECA4`: same-topic noise splitter.
- `ECA5`: conservative hybrid.
- `ECA6`: ECA5 plus unchanged citation gate projection.

## Model Comparison

| Model | Pass | Context Expected | Context Noise | Gate Expected | Gate Noise | Reasoning Drift | Planning Drift | Plan Cov | Resp Cov | Improved | Regressed |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ECA1 | `False` | `12` | `26` | `13` | `28` | `8` | `0` | `0.6333` | `0.6333` | `0` | `4` |
| ECA2 | `False` | `16` | `21` | `16` | `21` | `5` | `2` | `0.7333` | `0.7333` | `1` | `3` |
| ECA3 | `False` | `11` | `13` | `13` | `19` | `6` | `2` | `0.6333` | `0.6333` | `0` | `3` |
| ECA4 | `False` | `13` | `18` | `13` | `18` | `4` | `2` | `0.6333` | `0.6333` | `2` | `3` |
| ECA5 | `False` | `11` | `13` | `13` | `20` | `6` | `2` | `0.6333` | `0.6333` | `0` | `3` |
| ECA6 | `False` | `11` | `13` | `13` | `20` | `6` | `2` | `0.6333` | `0.6333` | `0` | `3` |

## Contextualization Examples

- `planning_failed_assumption`: context expected `3`, context noise `2`
- `causal_industrial_failure`: context expected `0`, context noise `0`
- `contradictory_evidence`: context expected `2`, context noise `2`
- `resource_allocation_shelters`: context expected `1`, context noise `4`
- `risk_uncertainty_planning`: context expected `0`, context noise `0`

## Expected-vs-Noise Contextual Alignment Analysis

Context-strong expected and context-strong noise counts are shown in the model comparison table.

## Unchanged Citation-Gate Outcome

The simulation does not globally loosen the citation gate; admitted concepts are projected through context metadata plus the existing citation-context path.

## Case-Level Improvements/Regressions

### ECA1
- `planning_failed_assumption`: `Under-Attending` -> `Reasoning Drift`
- `policy_audit_conflict`: `Planning Drift` -> `Reasoning Drift`
- `multi_step_failure_revision`: `Under-Attending` -> `Reasoning Drift`
- `logistics_proxy_planning`: `Under-Attending` -> `Reasoning Drift`

### ECA2
- `planning_failed_assumption`: `Under-Attending` -> `Reasoning Drift`
- `risk_uncertainty_planning`: `Reasoning Drift` -> `Under-Attending`
- `multi_step_failure_revision`: `Under-Attending` -> `Planning Drift`
- `logistics_proxy_planning`: `Under-Attending` -> `Reasoning Drift`

### ECA3
- `planning_failed_assumption`: `Under-Attending` -> `Reasoning Drift`
- `multi_step_failure_revision`: `Under-Attending` -> `Planning Drift`
- `logistics_proxy_planning`: `Under-Attending` -> `Reasoning Drift`

### ECA4
- `planning_failed_assumption`: `Under-Attending` -> `Reasoning Drift`
- `causal_industrial_failure`: `Reasoning Drift` -> `Under-Attending`
- `risk_uncertainty_planning`: `Reasoning Drift` -> `Under-Attending`
- `multi_step_failure_revision`: `Under-Attending` -> `Planning Drift`
- `logistics_proxy_planning`: `Under-Attending` -> `Reasoning Drift`

### ECA5
- `planning_failed_assumption`: `Under-Attending` -> `Reasoning Drift`
- `multi_step_failure_revision`: `Under-Attending` -> `Planning Drift`
- `logistics_proxy_planning`: `Under-Attending` -> `Reasoning Drift`

### ECA6
- `planning_failed_assumption`: `Under-Attending` -> `Reasoning Drift`
- `multi_step_failure_revision`: `Under-Attending` -> `Planning Drift`
- `logistics_proxy_planning`: `Under-Attending` -> `Reasoning Drift`

## Sparse/Unsupported Safety

Sparse and unsupported cases remained guarded by question-text cues only and stayed in every acceptance gate.

## Best Candidate

Passed candidates: `none`

## Rejected Candidates

- `ECA1` rejected: noise_no_increase, citable_noise_no_increase, reasoning_drift_no_increase, improves_failed_case
- `ECA2` rejected: noise_no_increase, citable_noise_no_increase, reasoning_drift_no_increase, planning_drift_no_increase
- `ECA3` rejected: noise_no_increase, citable_noise_no_increase, reasoning_drift_no_increase, planning_drift_no_increase, improves_failed_case
- `ECA4` rejected: noise_no_increase, citable_noise_no_increase, planning_drift_no_increase
- `ECA5` rejected: noise_no_increase, citable_noise_no_increase, reasoning_drift_no_increase, planning_drift_no_increase, improves_failed_case
- `ECA6` rejected: noise_no_increase, citable_noise_no_increase, reasoning_drift_no_increase, planning_drift_no_increase, improves_failed_case

## Live Prototype

Should be attempted later: `False`

## Continuation Checkpoint

- Model B default remains active: `True`
- Runtime files modified: `False`
- Raw archive: `G:\Delta_Dev\reports\runtime_v13_evidence_contextualization_activation_raw`

RUN_MORE_DIAGNICS
