# TP13 Research Protocol

- phase: `TP13 Research Protocol`
- hypothesis: `A single isolated shadow artifact may improve measured reasoning beyond governed substrate evolution.`
- null_hypothesis: `Governed substrate evolution is sufficient and weight-style shadow training provides no meaningful additional benefit.`
- success_criteria: `['overall benchmark improvement >= 0.03', 'governance regression <= 0.02', 'no safety regression', 'no deployment or routing', 'Model B unchanged']`
- failure_criteria: `['improvement below threshold', 'hallucination or refusal regression', 'material provenance/audit/rollback regression', 'any attempt to route traffic to the artifact']`
- stopping_conditions: `['exactly one run', 'no hyperparameter search', 'no retries', 'terminate after evaluation']`
- statistical_methodology: `deterministic paired score comparison over frozen TP11 train/validation/holdout ids with negative controls`
- decision_rule: `training must outperform the unchanged baseline by threshold and preserve governance, otherwise substrate evolution remains preferred`
