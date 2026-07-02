# Runtime V1.3 Expected Evidence Usability Audit

Generated: `2026-07-02T14:45:19`

Report-only audit. No runtime behavior, learning, validation, normalization, governance, storage, providers, candidate stores, canonical systems, benchmark fixtures, or default behavior was modified.

Current accepted default: Model B contextualized corpus support + citation_context reasoning usage gate

Final recommendation: `PROCEED_REASONING_CITATION_GATE_REVIEW`

## Summary

This audit classifies expected concepts by why QDA/ESS-style visibility does or does not become usable reasoning, planning, or response evidence.

## Why ESS Failed

ESS ended with `RUN_MORE_DIAGNOSTICS`. Visibility and lane separation clarified the failure, but expected evidence still did not reliably become safe response/reasoning evidence.

## Visible Expected Evidence Inventory

| Class | Count |
| --- | ---: |
| `visible_citable_and_used` | `6` |
| `visible_citable_not_response_bound` | `0` |
| `visible_rejected_by_citation_gate` | `11` |
| `visible_planning_only` | `1` |
| `visible_response_relevant_but_not_planning` | `0` |
| `visible_unsafe_due_same_topic_noise_risk` | `3` |
| `expected_benchmark_only_not_live_usable` | `1` |
| `unavailable_even_with_visibility` | `2` |

## Usability Classification Table

| Case | Rank | Visible | Attended | Reasoned | Planned | Responded | Class | Smallest Layer |
| --- | ---: | --- | --- | --- | --- | --- | --- | --- |
| `planning_failed_assumption` | `2` | `True` | `True` | `True` | `True` | `True` | `visible_citable_and_used` | `none` |
| `planning_failed_assumption` | `1` | `True` | `True` | `True` | `True` | `True` | `visible_citable_and_used` | `none` |
| `planning_failed_assumption` | `3` | `True` | `False` | `False` | `True` | `False` | `visible_planning_only` | `planning support binding` |
| `causal_industrial_failure` | `37` | `True` | `False` | `False` | `False` | `False` | `visible_rejected_by_citation_gate` | `reasoning citation gate` |
| `causal_industrial_failure` | `2` | `True` | `True` | `True` | `True` | `True` | `visible_citable_and_used` | `none` |
| `causal_industrial_failure` | `1` | `True` | `True` | `True` | `True` | `True` | `visible_citable_and_used` | `none` |
| `contradictory_evidence` | `2` | `True` | `False` | `False` | `False` | `False` | `visible_rejected_by_citation_gate` | `reasoning citation gate` |
| `contradictory_evidence` | `7` | `True` | `False` | `False` | `False` | `False` | `visible_rejected_by_citation_gate` | `reasoning citation gate` |
| `contradictory_evidence` | `3` | `True` | `False` | `False` | `False` | `False` | `visible_rejected_by_citation_gate` | `reasoning citation gate` |
| `resource_allocation_shelters` | `1` | `True` | `False` | `False` | `False` | `False` | `visible_rejected_by_citation_gate` | `reasoning citation gate` |
| `resource_allocation_shelters` | `11` | `True` | `False` | `False` | `False` | `False` | `visible_rejected_by_citation_gate` | `reasoning citation gate` |
| `resource_allocation_shelters` | `18` | `True` | `False` | `False` | `False` | `False` | `visible_rejected_by_citation_gate` | `reasoning citation gate` |
| `risk_uncertainty_planning` | `4` | `True` | `False` | `False` | `False` | `False` | `visible_unsafe_due_same_topic_noise_risk` | `evidence contextualization in activation` |
| `risk_uncertainty_planning` | `None` | `False` | `False` | `False` | `False` | `False` | `expected_benchmark_only_not_live_usable` | `benchmark/live-window review` |
| `risk_uncertainty_planning` | `2` | `False` | `False` | `False` | `False` | `False` | `unavailable_even_with_visibility` | `activation visibility` |
| `policy_audit_conflict` | `37` | `True` | `False` | `False` | `False` | `False` | `visible_rejected_by_citation_gate` | `reasoning citation gate` |
| `policy_audit_conflict` | `22` | `True` | `False` | `False` | `False` | `False` | `visible_rejected_by_citation_gate` | `reasoning citation gate` |
| `policy_audit_conflict` | `1` | `True` | `True` | `True` | `True` | `True` | `visible_citable_and_used` | `none` |
| `multi_step_failure_revision` | `40` | `True` | `False` | `False` | `False` | `False` | `visible_unsafe_due_same_topic_noise_risk` | `evidence contextualization in activation` |
| `multi_step_failure_revision` | `1` | `True` | `True` | `True` | `True` | `True` | `visible_citable_and_used` | `none` |
| `multi_step_failure_revision` | `6` | `True` | `False` | `False` | `False` | `False` | `visible_unsafe_due_same_topic_noise_risk` | `evidence contextualization in activation` |
| `logistics_proxy_planning` | `1` | `False` | `True` | `True` | `True` | `True` | `unavailable_even_with_visibility` | `activation visibility` |
| `logistics_proxy_planning` | `4` | `True` | `False` | `False` | `False` | `False` | `visible_rejected_by_citation_gate` | `reasoning citation gate` |
| `logistics_proxy_planning` | `24` | `True` | `False` | `False` | `False` | `False` | `visible_rejected_by_citation_gate` | `reasoning citation gate` |

## Case-Level Bottleneck Table

- `causal_industrial_failure`: visible_rejected_by_citation_gate: 1, visible_citable_and_used: 2
- `contradictory_evidence`: visible_rejected_by_citation_gate: 3
- `logistics_proxy_planning`: unavailable_even_with_visibility: 1, visible_rejected_by_citation_gate: 2
- `multi_step_failure_revision`: visible_unsafe_due_same_topic_noise_risk: 2, visible_citable_and_used: 1
- `planning_failed_assumption`: visible_citable_and_used: 2, visible_planning_only: 1
- `policy_audit_conflict`: visible_rejected_by_citation_gate: 2, visible_citable_and_used: 1
- `resource_allocation_shelters`: visible_rejected_by_citation_gate: 3
- `risk_uncertainty_planning`: visible_unsafe_due_same_topic_noise_risk: 1, expected_benchmark_only_not_live_usable: 1, unavailable_even_with_visibility: 1

## Citation-Gate Rejection Analysis

Visible concepts rejected by citation gate: `11`

## Response-Binding Failure Analysis

Citable but not response-bound concepts: `0`

## Planning-Only Evidence Analysis

Visible planning-only concepts: `1`

## Same-Topic Noise Risk Analysis

Visible expected concepts dominated by same-topic noise risk: `3`

## Benchmark/Live-Usability Analysis

Benchmark-only or outside-live-window concepts: `1`

## Dominant Next Bottleneck

`citation gate too strict`

## Recommended Next Experiment

`PROCEED_REASONING_CITATION_GATE_REVIEW`

## Continuation Checkpoint

- Model B default remains active: `True`
- Runtime files modified: `False`
- Raw archive: `G:\Delta_Dev\reports\runtime_v13_expected_evidence_usability_raw`

PROCEED_REASONING_CITATION_GATE_REVIEW
