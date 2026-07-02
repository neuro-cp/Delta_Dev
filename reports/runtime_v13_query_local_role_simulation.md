# Runtime V1.3 Query-Local Role Simulation

Final recommendation: `PROCEED_ROLE_MODEL_R4`

This is a read-only simulation. It does not modify live runtime behavior, learning, governance, storage, activation recurrence, or canonical knowledge.

## Summary

- current Model B decision: `ACCEPT_RUNTIME_V13_QUERY_EVIDENCE_MODEL_B`
- remaining noise count: `7`
- accepted role models: `['R4', 'R2', 'R3']`
- recommended model: `R4`

## Current Model B Metrics

| Metric | Current Model B |
| --- | ---: |
| noise_used_in_reasoning | `7.0` |
| reasoning_drift_cases | `4.0` |
| planning_drift_cases | `1.0` |
| response_drift_cases | `0.0` |
| attention_precision | `0.6333` |
| attention_recall | `0.4333` |
| planning_core_coverage | `0.4333` |
| response_core_coverage | `0.4333` |
| grounding_score | `1.0` |
| hallucinations | `0.0` |
| expected_outside_top_10 | `8` |
| expected_outside_top_20 | `6` |
| mean_expected_rank | `10` |
| mean_noise_above_expected | `9.7083` |

## Per-Role-Model Projected Metrics

| Model | Proceed | Noise Evidence | Reasoning Drift | Planning Drift | Response Drift | Attention Precision | Attention Recall | Planning Core | Response Core | Failed Gates |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| R1 Strict Core Evidence | `False` | `0` | `0` | `2` | `2` | `1.0` | `0.7143` | `0.7143` | `0.7143` | planning_drift_increased, response_drift_increased, expected_concepts_blocked_from_needed_use |
| R2 Supporting Context Split | `True` | `1` | `1` | `0` | `0` | `0.9` | `1.0` | `1.0` | `1.0` | none |
| R3 Citation-Only Role Gate | `True` | `1` | `1` | `0` | `0` | `0.9` | `1.0` | `1.0` | `1.0` | none |
| R4 Hybrid Role Gate | `True` | `1` | `1` | `0` | `0` | `0.9` | `1.0` | `1.0` | `1.0` | none |

## R1 - Strict Core Evidence

- can proceed: `False`
- role counts: `{'Core Evidence': 5, 'Supporting Context': 8, 'Peripheral Context': 1}`
- concepts moved from evidence to supporting context: `6`
- expected concepts downgraded/blocked: `2`
- useful neighbors blocked: `0`

### Remaining Noisy Concept Roles
- `causal_industrial_failure` / `0fb23c0b-b877-4cf2-a66d-94d927b77542` -> `Non-Evidence`: The uncertainty in this scenario lies in the potential confounding variables and the complexity of real world industrial settings where multiple factors can interact
- `causal_industrial_failure` / `183718d2-9612-4057-94b7-4ad8fd896278` -> `Non-Evidence`: For instance, if increased maintenance frequency is correlated with higher equipment failure rates, it might be tempting to conclude that frequent maintenance causes failures
- `causal_industrial_failure` / `9d5b7363-5857-4091-8449-9374d6b4b68f` -> `Non-Evidence`: The current understanding is that causal relationships in industrial maintenance are complex and can be influenced by various factors leading to uncertainty in predicting
- `causal_industrial_failure` / `c5cc234b-b4ae-4f0c-98f7-c7f04e320abf` -> `Non-Evidence`: For instance if a maintenance team observes that a machine s downtime is correlated with a specific type of weather they might mistakenly conclude
- `contradictory_evidence` / `ef940f21-c49c-41f8-b86e-12a02a0f37f6` -> `Non-Evidence`: If the sources are found to be the same, it would suggest that one or both of the reports are inaccurate or contradictory
- `resource_allocation_shelters` / `f567a38f-be7c-4783-972f-d82e8fb2e36f` -> `Non-Evidence`: When allocating resources for emergency shelters the tradeoff is between meeting the immediate needs of the priority group and ensuring that the allocation can
- `risk_uncertainty_planning` / `d3d08fe0-dbf7-437d-9c46-5c1253dbf9ab` -> `Non-Evidence`: Uncertainty The certainty of the revised plan depends on the specific requirements and regulations of the project s location as well as the potential

### Case-Level Impact
- `planning_failed_assumption` reasoned `2 -> 1`, planning `2 -> 1`, response `2 -> 1`, noise evidence `0 -> 0`, supporting context `1`
- `causal_industrial_failure` reasoned `6 -> 2`, planning `5 -> 2`, response `5 -> 2`, noise evidence `4 -> 0`, supporting context `4`
- `contradictory_evidence` reasoned `1 -> 0`, planning `1 -> 0`, response `1 -> 0`, noise evidence `1 -> 0`, supporting context `1`
- `resource_allocation_shelters` reasoned `1 -> 0`, planning `1 -> 0`, response `1 -> 0`, noise evidence `1 -> 0`, supporting context `1`
- `risk_uncertainty_planning` reasoned `1 -> 0`, planning `1 -> 0`, response `1 -> 0`, noise evidence `1 -> 0`, supporting context `0`
- `policy_audit_conflict` reasoned `1 -> 0`, planning `1 -> 0`, response `1 -> 0`, noise evidence `0 -> 0`, supporting context `1`
- `multi_step_failure_revision` reasoned `1 -> 1`, planning `1 -> 1`, response `1 -> 1`, noise evidence `0 -> 0`, supporting context `0`
- `logistics_proxy_planning` reasoned `1 -> 1`, planning `1 -> 1`, response `1 -> 1`, noise evidence `0 -> 0`, supporting context `0`

## R2 - Supporting Context Split

- can proceed: `True`
- role counts: `{'Core Evidence': 7, 'Supporting Context': 7}`
- concepts moved from evidence to supporting context: `7`
- expected concepts downgraded/blocked: `0`
- useful neighbors blocked: `0`

### Remaining Noisy Concept Roles
- `causal_industrial_failure` / `0fb23c0b-b877-4cf2-a66d-94d927b77542` -> `Non-Evidence`: The uncertainty in this scenario lies in the potential confounding variables and the complexity of real world industrial settings where multiple factors can interact
- `causal_industrial_failure` / `183718d2-9612-4057-94b7-4ad8fd896278` -> `Non-Evidence`: For instance, if increased maintenance frequency is correlated with higher equipment failure rates, it might be tempting to conclude that frequent maintenance causes failures
- `causal_industrial_failure` / `9d5b7363-5857-4091-8449-9374d6b4b68f` -> `Non-Evidence`: The current understanding is that causal relationships in industrial maintenance are complex and can be influenced by various factors leading to uncertainty in predicting
- `causal_industrial_failure` / `c5cc234b-b4ae-4f0c-98f7-c7f04e320abf` -> `Non-Evidence`: For instance if a maintenance team observes that a machine s downtime is correlated with a specific type of weather they might mistakenly conclude
- `contradictory_evidence` / `ef940f21-c49c-41f8-b86e-12a02a0f37f6` -> `Non-Evidence`: If the sources are found to be the same, it would suggest that one or both of the reports are inaccurate or contradictory
- `resource_allocation_shelters` / `f567a38f-be7c-4783-972f-d82e8fb2e36f` -> `Non-Evidence`: When allocating resources for emergency shelters the tradeoff is between meeting the immediate needs of the priority group and ensuring that the allocation can
- `risk_uncertainty_planning` / `d3d08fe0-dbf7-437d-9c46-5c1253dbf9ab` -> `Non-Evidence`: Uncertainty The certainty of the revised plan depends on the specific requirements and regulations of the project s location as well as the potential

### Case-Level Impact
- `planning_failed_assumption` reasoned `2 -> 2`, planning `2 -> 2`, response `2 -> 2`, noise evidence `0 -> 0`, supporting context `0`
- `causal_industrial_failure` reasoned `6 -> 6`, planning `5 -> 2`, response `5 -> 2`, noise evidence `4 -> 0`, supporting context `4`
- `contradictory_evidence` reasoned `1 -> 1`, planning `1 -> 0`, response `1 -> 0`, noise evidence `1 -> 0`, supporting context `1`
- `resource_allocation_shelters` reasoned `1 -> 1`, planning `1 -> 0`, response `1 -> 0`, noise evidence `1 -> 0`, supporting context `1`
- `risk_uncertainty_planning` reasoned `1 -> 1`, planning `1 -> 0`, response `1 -> 0`, noise evidence `1 -> 0`, supporting context `1`
- `policy_audit_conflict` reasoned `1 -> 1`, planning `1 -> 1`, response `1 -> 1`, noise evidence `0 -> 0`, supporting context `0`
- `multi_step_failure_revision` reasoned `1 -> 1`, planning `1 -> 1`, response `1 -> 1`, noise evidence `0 -> 0`, supporting context `0`
- `logistics_proxy_planning` reasoned `1 -> 1`, planning `1 -> 1`, response `1 -> 1`, noise evidence `0 -> 0`, supporting context `0`

## R3 - Citation-Only Role Gate

- can proceed: `True`
- role counts: `{'Core Evidence': 7, 'Supporting Context': 7}`
- concepts moved from evidence to supporting context: `7`
- expected concepts downgraded/blocked: `0`
- useful neighbors blocked: `0`

### Remaining Noisy Concept Roles
- `causal_industrial_failure` / `0fb23c0b-b877-4cf2-a66d-94d927b77542` -> `Non-Evidence`: The uncertainty in this scenario lies in the potential confounding variables and the complexity of real world industrial settings where multiple factors can interact
- `causal_industrial_failure` / `183718d2-9612-4057-94b7-4ad8fd896278` -> `Non-Evidence`: For instance, if increased maintenance frequency is correlated with higher equipment failure rates, it might be tempting to conclude that frequent maintenance causes failures
- `causal_industrial_failure` / `9d5b7363-5857-4091-8449-9374d6b4b68f` -> `Non-Evidence`: The current understanding is that causal relationships in industrial maintenance are complex and can be influenced by various factors leading to uncertainty in predicting
- `causal_industrial_failure` / `c5cc234b-b4ae-4f0c-98f7-c7f04e320abf` -> `Non-Evidence`: For instance if a maintenance team observes that a machine s downtime is correlated with a specific type of weather they might mistakenly conclude
- `contradictory_evidence` / `ef940f21-c49c-41f8-b86e-12a02a0f37f6` -> `Non-Evidence`: If the sources are found to be the same, it would suggest that one or both of the reports are inaccurate or contradictory
- `resource_allocation_shelters` / `f567a38f-be7c-4783-972f-d82e8fb2e36f` -> `Non-Evidence`: When allocating resources for emergency shelters the tradeoff is between meeting the immediate needs of the priority group and ensuring that the allocation can
- `risk_uncertainty_planning` / `d3d08fe0-dbf7-437d-9c46-5c1253dbf9ab` -> `Non-Evidence`: Uncertainty The certainty of the revised plan depends on the specific requirements and regulations of the project s location as well as the potential

### Case-Level Impact
- `planning_failed_assumption` reasoned `2 -> 2`, planning `2 -> 2`, response `2 -> 2`, noise evidence `0 -> 0`, supporting context `0`
- `causal_industrial_failure` reasoned `6 -> 6`, planning `5 -> 2`, response `5 -> 2`, noise evidence `4 -> 0`, supporting context `4`
- `contradictory_evidence` reasoned `1 -> 1`, planning `1 -> 0`, response `1 -> 0`, noise evidence `1 -> 0`, supporting context `1`
- `resource_allocation_shelters` reasoned `1 -> 1`, planning `1 -> 0`, response `1 -> 0`, noise evidence `1 -> 0`, supporting context `1`
- `risk_uncertainty_planning` reasoned `1 -> 1`, planning `1 -> 0`, response `1 -> 0`, noise evidence `1 -> 0`, supporting context `1`
- `policy_audit_conflict` reasoned `1 -> 1`, planning `1 -> 1`, response `1 -> 1`, noise evidence `0 -> 0`, supporting context `0`
- `multi_step_failure_revision` reasoned `1 -> 1`, planning `1 -> 1`, response `1 -> 1`, noise evidence `0 -> 0`, supporting context `0`
- `logistics_proxy_planning` reasoned `1 -> 1`, planning `1 -> 1`, response `1 -> 1`, noise evidence `0 -> 0`, supporting context `0`

## R4 - Hybrid Role Gate

- can proceed: `True`
- role counts: `{'Core Evidence': 7, 'Supporting Context': 6, 'Peripheral Context': 1}`
- concepts moved from evidence to supporting context: `6`
- expected concepts downgraded/blocked: `0`
- useful neighbors blocked: `0`

### Remaining Noisy Concept Roles
- `causal_industrial_failure` / `0fb23c0b-b877-4cf2-a66d-94d927b77542` -> `Non-Evidence`: The uncertainty in this scenario lies in the potential confounding variables and the complexity of real world industrial settings where multiple factors can interact
- `causal_industrial_failure` / `183718d2-9612-4057-94b7-4ad8fd896278` -> `Non-Evidence`: For instance, if increased maintenance frequency is correlated with higher equipment failure rates, it might be tempting to conclude that frequent maintenance causes failures
- `causal_industrial_failure` / `9d5b7363-5857-4091-8449-9374d6b4b68f` -> `Non-Evidence`: The current understanding is that causal relationships in industrial maintenance are complex and can be influenced by various factors leading to uncertainty in predicting
- `causal_industrial_failure` / `c5cc234b-b4ae-4f0c-98f7-c7f04e320abf` -> `Non-Evidence`: For instance if a maintenance team observes that a machine s downtime is correlated with a specific type of weather they might mistakenly conclude
- `contradictory_evidence` / `ef940f21-c49c-41f8-b86e-12a02a0f37f6` -> `Non-Evidence`: If the sources are found to be the same, it would suggest that one or both of the reports are inaccurate or contradictory
- `resource_allocation_shelters` / `f567a38f-be7c-4783-972f-d82e8fb2e36f` -> `Non-Evidence`: When allocating resources for emergency shelters the tradeoff is between meeting the immediate needs of the priority group and ensuring that the allocation can
- `risk_uncertainty_planning` / `d3d08fe0-dbf7-437d-9c46-5c1253dbf9ab` -> `Non-Evidence`: Uncertainty The certainty of the revised plan depends on the specific requirements and regulations of the project s location as well as the potential

### Case-Level Impact
- `planning_failed_assumption` reasoned `2 -> 2`, planning `2 -> 2`, response `2 -> 2`, noise evidence `0 -> 0`, supporting context `0`
- `causal_industrial_failure` reasoned `6 -> 6`, planning `5 -> 2`, response `5 -> 2`, noise evidence `4 -> 0`, supporting context `4`
- `contradictory_evidence` reasoned `1 -> 1`, planning `1 -> 0`, response `1 -> 0`, noise evidence `1 -> 0`, supporting context `1`
- `resource_allocation_shelters` reasoned `1 -> 1`, planning `1 -> 0`, response `1 -> 0`, noise evidence `1 -> 0`, supporting context `1`
- `risk_uncertainty_planning` reasoned `1 -> 0`, planning `1 -> 0`, response `1 -> 0`, noise evidence `1 -> 0`, supporting context `0`
- `policy_audit_conflict` reasoned `1 -> 1`, planning `1 -> 1`, response `1 -> 1`, noise evidence `0 -> 0`, supporting context `0`
- `multi_step_failure_revision` reasoned `1 -> 1`, planning `1 -> 1`, response `1 -> 1`, noise evidence `0 -> 0`, supporting context `0`
- `logistics_proxy_planning` reasoned `1 -> 1`, planning `1 -> 1`, response `1 -> 1`, noise evidence `0 -> 0`, supporting context `0`

## Interpretation

The strongest simulated shape is to split citable evidence from query-local context. Near-neighbor concepts remain available as Supporting Context, but only Core Evidence contributes to evidence keys, planning citations, and response citations.

`PROCEED_ROLE_MODEL_R4`
