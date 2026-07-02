# Phase B Runtime Scorecards

| Case | Category | Pass | Retrieval Precision | Retrieval Recall | Attention Precision | Attention Recall | Grounding | Used Noise | Suppressed Core |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| gps_drift_retrieval | retrieval_accuracy | `True` | `0.75` | `1.0` | `1.0` | `1.0` | `1.0` | `0` | `0` |
| snowstorm_grounded_planning | planning | `False` | `0.6` | `1.0` | `1.0` | `1.0` | `1.0` | `0` | `0` |
| salt_tradeoff_conflict | conflict_handling | `False` | `0.3333` | `1.0` | `1.0` | `1.0` | `1.0` | `0` | `0` |
| resource_allocation_calibration | confidence_calibration | `False` | `0.3333` | `1.0` | `1.0` | `1.0` | `1.0` | `0` | `0` |
| sparse_violin_question | sparse_knowledge | `True` | `1.0` | `1.0` | `1.0` | `1.0` | `1.0` | `0` | `0` |
| repeat_snowstorm_stability | runtime_stability | `False` | `0.6` | `1.0` | `1.0` | `1.0` | `1.0` | `0` | `0` |
