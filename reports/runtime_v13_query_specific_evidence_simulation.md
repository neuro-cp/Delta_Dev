# Runtime V1.3 Query-Specific Evidence Simulation

Final recommendation: `PROCEED_QUERY_EVIDENCE_MODEL_B`

This is a read-only simulation. It does not modify live runtime behavior, learning, governance, storage, activation recurrence, or canonical knowledge.

## Summary

- previous diagnostic: `PROCEED_QUERY_SPECIFIC_EVIDENCE_MODELING`
- accepted models: `['model_b_contextualized_corpus_support']`
- recommended model: `model_b_contextualized_corpus_support`

## Baseline / Current Metrics

| Metric | V1.2 Baseline | Refined V1.3 Current |
| --- | ---: | ---: |
| noise_used_in_reasoning | `12.0` | `8.0` |
| reasoning_drift_cases | `5.0` | `5.0` |
| attention_precision | `0.55` | `0.5833` |
| attention_recall | `0.4333` | `0.4333` |
| planning_core_coverage | `0.4333` | `0.4333` |
| response_core_coverage | `0.4333` | `0.4333` |
| grounding_score | `1.0` | `1.0` |
| hallucinations | `0.0` | `0.0` |
| retrieval_recall | `0.5333` | `0.5333` |
| retrieval_precision | `0.16` | `0.16` |

## Per-Model Projected Metrics

| Model | Proceed | Noise Used | Drift Cases | Attention Precision | Attention Recall | Planning Core | Response Core | Failed Gates |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| model_a_specific_overlap_floor | `False` | `5` | `2` | `0.5455` | `0.8571` | `0.8571` | `0.8571` | expected_concepts_blocked |
| model_b_contextualized_corpus_support | `True` | `6` | `3` | `0.5385` | `1.0` | `1.0` | `1.0` | none |
| model_c_generic_anchor_discount | `False` | `6` | `3` | `0.4545` | `0.7143` | `0.7143` | `0.7143` | expected_concepts_blocked |
| model_d_concept_action_alignment | `False` | `3` | `2` | `0.5714` | `0.5714` | `0.5714` | `0.5714` | expected_concepts_blocked |
| model_e_hybrid_query_evidence_score | `False` | `5` | `2` | `0.5455` | `0.8571` | `0.8571` | `0.8571` | expected_concepts_blocked |

## model_a_specific_overlap_floor

- can proceed: `False`
- failed gates: `['expected_concepts_blocked']`
- blocked noisy concepts: `3`
- blocked expected concepts: `1`
- blocked useful neighbors: `0`

### Blocked Noise
- `resource_allocation_shelters` / `f567a38f-be7c-4783-972f-d82e8fb2e36f` score `0.0`: When allocating resources for emergency shelters the tradeoff is between meeting the immediate needs of the priority group and ensuring that the allocation can
- `risk_uncertainty_planning` / `d3d08fe0-dbf7-437d-9c46-5c1253dbf9ab` score `0.0`: Uncertainty The certainty of the revised plan depends on the specific requirements and regulations of the project s location as well as the potential
- `multi_step_failure_revision` / `fec7285c-8ebf-45ba-8197-911a515e4e0b` score `0.0`: To predict cascade risk, failure drills can be used to identify dependencies and tradeoffs within the system

### Accidentally Blocked Expected/Useful Concepts
- `logistics_proxy_planning` / `76120648-7522-4025-8176-5e5fb199c687` (Core) score `0.0`: When the emergency response plan is disrupted due to a failed permit assumption the team should use resource telemetry data to assess the current

### Case-Level Impact
- `resource_allocation_shelters` reasoned `1 -> 0`, noise `1 -> 0`, core `0 -> 0`
- `risk_uncertainty_planning` reasoned `1 -> 0`, noise `1 -> 0`, core `0 -> 0`
- `multi_step_failure_revision` reasoned `2 -> 1`, noise `1 -> 0`, core `1 -> 1`
- `logistics_proxy_planning` reasoned `1 -> 0`, noise `0 -> 0`, core `1 -> 0`

## model_b_contextualized_corpus_support

- can proceed: `True`
- failed gates: `[]`
- blocked noisy concepts: `2`
- blocked expected concepts: `0`
- blocked useful neighbors: `0`

### Blocked Noise
- `risk_uncertainty_planning` / `d3d08fe0-dbf7-437d-9c46-5c1253dbf9ab` score `0.25`: Uncertainty The certainty of the revised plan depends on the specific requirements and regulations of the project s location as well as the potential
- `multi_step_failure_revision` / `fec7285c-8ebf-45ba-8197-911a515e4e0b` score `0.25`: To predict cascade risk, failure drills can be used to identify dependencies and tradeoffs within the system

### Accidentally Blocked Expected/Useful Concepts
- none

### Case-Level Impact
- `risk_uncertainty_planning` reasoned `1 -> 0`, noise `1 -> 0`, core `0 -> 0`
- `multi_step_failure_revision` reasoned `2 -> 1`, noise `1 -> 0`, core `1 -> 1`

## model_c_generic_anchor_discount

- can proceed: `False`
- failed gates: `['expected_concepts_blocked']`
- blocked noisy concepts: `2`
- blocked expected concepts: `2`
- blocked useful neighbors: `0`

### Blocked Noise
- `risk_uncertainty_planning` / `d3d08fe0-dbf7-437d-9c46-5c1253dbf9ab` score `0.2`: Uncertainty The certainty of the revised plan depends on the specific requirements and regulations of the project s location as well as the potential
- `multi_step_failure_revision` / `fec7285c-8ebf-45ba-8197-911a515e4e0b` score `0.2`: To predict cascade risk, failure drills can be used to identify dependencies and tradeoffs within the system

### Accidentally Blocked Expected/Useful Concepts
- `planning_failed_assumption` / `aa6c1ba8-9c57-474c-afa5-7383a4733cae` (Core) score `0.2`: When the emergency response plan is disrupted due to a failed permit assumption, the first step is to review the inspection records to determine the severity of the issue
- `multi_step_failure_revision` / `4b01b020-00b1-4d40-9422-aba2288625d4` (Core) score `0.2`: By analyzing the likely failure points and the evidence required to revise the plan, a robust response can be maintained

### Case-Level Impact
- `planning_failed_assumption` reasoned `2 -> 1`, noise `0 -> 0`, core `2 -> 1`
- `risk_uncertainty_planning` reasoned `1 -> 0`, noise `1 -> 0`, core `0 -> 0`
- `multi_step_failure_revision` reasoned `2 -> 0`, noise `1 -> 0`, core `1 -> 0`

## model_d_concept_action_alignment

- can proceed: `False`
- failed gates: `['expected_concepts_blocked']`
- blocked noisy concepts: `5`
- blocked expected concepts: `3`
- blocked useful neighbors: `0`

### Blocked Noise
- `causal_industrial_failure` / `0fb23c0b-b877-4cf2-a66d-94d927b77542` score `0.1`: The uncertainty in this scenario lies in the potential confounding variables and the complexity of real world industrial settings where multiple factors can interact
- `causal_industrial_failure` / `c5cc234b-b4ae-4f0c-98f7-c7f04e320abf` score `0.1`: For instance if a maintenance team observes that a machine s downtime is correlated with a specific type of weather they might mistakenly conclude
- `contradictory_evidence` / `ef940f21-c49c-41f8-b86e-12a02a0f37f6` score `0.1`: If the sources are found to be the same, it would suggest that one or both of the reports are inaccurate or contradictory
- `risk_uncertainty_planning` / `d3d08fe0-dbf7-437d-9c46-5c1253dbf9ab` score `0.1`: Uncertainty The certainty of the revised plan depends on the specific requirements and regulations of the project s location as well as the potential
- `multi_step_failure_revision` / `fec7285c-8ebf-45ba-8197-911a515e4e0b` score `0.1`: To predict cascade risk, failure drills can be used to identify dependencies and tradeoffs within the system

### Accidentally Blocked Expected/Useful Concepts
- `planning_failed_assumption` / `76120648-7522-4025-8176-5e5fb199c687` (Core) score `0.1`: When the emergency response plan is disrupted due to a failed permit assumption the team should use resource telemetry data to assess the current
- `policy_audit_conflict` / `acaca659-aee5-4cef-9c4c-5a2281c1a9ef` (Core) score `0.1`: Reflecting on uncertainty it is possible that the policy and the audit findings are both correct in their own contexts but the records do
- `logistics_proxy_planning` / `76120648-7522-4025-8176-5e5fb199c687` (Core) score `0.1`: When the emergency response plan is disrupted due to a failed permit assumption the team should use resource telemetry data to assess the current

### Case-Level Impact
- `planning_failed_assumption` reasoned `2 -> 1`, noise `0 -> 0`, core `2 -> 1`
- `causal_industrial_failure` reasoned `6 -> 4`, noise `4 -> 2`, core `2 -> 2`
- `contradictory_evidence` reasoned `1 -> 0`, noise `1 -> 0`, core `0 -> 0`
- `risk_uncertainty_planning` reasoned `1 -> 0`, noise `1 -> 0`, core `0 -> 0`
- `policy_audit_conflict` reasoned `1 -> 0`, noise `0 -> 0`, core `1 -> 0`
- `multi_step_failure_revision` reasoned `2 -> 1`, noise `1 -> 0`, core `1 -> 1`
- `logistics_proxy_planning` reasoned `1 -> 0`, noise `0 -> 0`, core `1 -> 0`

## model_e_hybrid_query_evidence_score

- can proceed: `False`
- failed gates: `['expected_concepts_blocked']`
- blocked noisy concepts: `3`
- blocked expected concepts: `1`
- blocked useful neighbors: `0`

### Blocked Noise
- `resource_allocation_shelters` / `f567a38f-be7c-4783-972f-d82e8fb2e36f` score `0.3362`: When allocating resources for emergency shelters the tradeoff is between meeting the immediate needs of the priority group and ensuring that the allocation can
- `risk_uncertainty_planning` / `d3d08fe0-dbf7-437d-9c46-5c1253dbf9ab` score `0.0135`: Uncertainty The certainty of the revised plan depends on the specific requirements and regulations of the project s location as well as the potential
- `multi_step_failure_revision` / `fec7285c-8ebf-45ba-8197-911a515e4e0b` score `-0.0159`: To predict cascade risk, failure drills can be used to identify dependencies and tradeoffs within the system

### Accidentally Blocked Expected/Useful Concepts
- `logistics_proxy_planning` / `76120648-7522-4025-8176-5e5fb199c687` (Core) score `0.2542`: When the emergency response plan is disrupted due to a failed permit assumption the team should use resource telemetry data to assess the current

### Case-Level Impact
- `resource_allocation_shelters` reasoned `1 -> 0`, noise `1 -> 0`, core `0 -> 0`
- `risk_uncertainty_planning` reasoned `1 -> 0`, noise `1 -> 0`, core `0 -> 0`
- `multi_step_failure_revision` reasoned `2 -> 1`, noise `1 -> 0`, core `1 -> 1`
- `logistics_proxy_planning` reasoned `1 -> 0`, noise `0 -> 0`, core `1 -> 0`

## Explicitly Rejected Models

- `model_a_specific_overlap_floor`: ['expected_concepts_blocked']
- `model_c_generic_anchor_discount`: ['expected_concepts_blocked']
- `model_d_concept_action_alignment`: ['expected_concepts_blocked']
- `model_e_hybrid_query_evidence_score`: ['expected_concepts_blocked']

## Interpretation

The simulation treats corpus support and query-specific evidence as separate signals. A model is eligible only when it reduces or preserves noisy reasoning while blocking no expected concepts or useful neighbors and preserving planning/response coverage by projection.

`PROCEED_QUERY_EVIDENCE_MODEL_B`
