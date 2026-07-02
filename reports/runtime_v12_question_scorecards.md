# Runtime V1.2 Question Scorecards

| Case | Category | Retrieval Recall | Attention Recall | Noise Used | Grounding | Planning Coverage | Response Coverage | Decision |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| planning_failed_assumption | planning | `1.0` | `0.6667` | `0` | `1.0` | `0.6667` | `0.6667` | `Under-Attending` |
| causal_industrial_failure | causal_reasoning | `0.6667` | `0.6667` | `4` | `1.0` | `0.6667` | `0.6667` | `Reasoning Drift` |
| contradictory_evidence | contradiction_handling | `1.0` | `0.0` | `1` | `1.0` | `0.0` | `0.0` | `Reasoning Drift` |
| resource_allocation_shelters | resource_allocation | `0.3333` | `0.0` | `1` | `1.0` | `0.0` | `0.0` | `Reasoning Drift` |
| risk_uncertainty_planning | risk_assessment | `0.6667` | `0.0` | `1` | `1.0` | `0.0` | `0.0` | `Reasoning Drift` |
| policy_audit_conflict | conflicting_evidence | `0.3333` | `0.3333` | `0` | `1.0` | `0.3333` | `0.3333` | `Planning Drift` |
| multi_step_failure_revision | multi_step_reasoning | `0.6667` | `0.3333` | `0` | `1.0` | `0.3333` | `0.3333` | `Under-Attending` |
| logistics_proxy_planning | logistics | `0.6667` | `0.3333` | `0` | `1.0` | `0.3333` | `0.3333` | `Under-Attending` |
| sparse_violin_tuning | sparse_knowledge | `0.0` | `1.0` | `0` | `1.0` | `1.0` | `1.0` | `Healthy` |
| unsupported_recipe | unsupported_questions | `0.0` | `1.0` | `0` | `1.0` | `1.0` | `1.0` | `Healthy` |
